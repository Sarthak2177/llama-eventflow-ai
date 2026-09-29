from typing import Annotated, Literal, Sequence, TypedDict
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage
from langchain_ollama import ChatOllama
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

from . import config
from .agent_tools import ALL_TOOLS
from .tool_selector import select_relevant_tools

class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    session_id: str

MUTATING_TOOLS = {
    "duplicate_solace_entity",
    "update_entity_relationship",
    "create_solace_entity",
    "create_solace_entity_version",
    "delete_solace_entity",
    "delete_solace_entity_version",
}

# Add action specific mutating checking for broker tools
def is_mutating_tool_call(tc) -> bool:
    name = tc["name"]
    if name in MUTATING_TOOLS:
        return True
    if name in ["manage_solace_queue", "manage_queue_subscription"]:
        args = tc.get("args", {})
        action = args.get("action", "")
        if action in ["create", "update", "delete", "duplicate", "add", "remove"]:
            return True
    return False

def get_llm():
    try:
        return ChatOllama(model=config.LLM_MODEL, base_url=config.LLM_BASE_URL, temperature=0.1, num_ctx=16384)
    except Exception as e:
        print(f"Failed to initialize LLM: {e}")
        return None

SYSTEM_PROMPT = """You are EventFlow AI, an expert assistant for the Solace Event Portal.
You help users understand their Event-Driven Architecture.

You have access to "Smart Tools" that automatically navigate the complex Solace API for you.
Always follow this logic:
1. If you need to list entities of a certain type or find an entity by name, use `search_solace_entity`.
2. If you need to find what an entity contains, produces, or consumes (e.g. finding Event APIs included in an Event API Product), use `get_entity_relationships` with its ID.
3. If you need to find what other entities rely on, reference, or will be affected by a given entity, use `get_entity_impact` with its version ID. For multi-hop impact (e.g., finding Event API Products affected by an Event), you must call `get_entity_impact` sequentially on the intermediate results.
4. If you need to read the data fields, payload, or schema of an event, use `get_schema_content` with the Event ID.
5. To check live queue statistics, message counts, or connected consumers on the Event Broker, use `get_queue_stats`.
6. To check the ACL profile or configuration of a specific client username on the Event Broker, use `get_client_username`.
7. If you are asked to find which queues have a specific condition (e.g. no consumers, accumulating messages), use `list_queues` to get a bulk telemetry array and filter it yourself.
8. In this environment, a queue provisioned for an application generally shares the exact name as the application. To inspect it, use `get_queue_stats` with the application's name.

When answering, always be concise and structured. Use bullet points.
Never fabricate data — only report what the tools return.

For Create, Update, or Delete operations, the system will pause and ask the user for approval. Do NOT hallucinate IDs, always search for them first.
"""

def should_continue(state: AgentState) -> Literal["tools", "__end__"]:
    messages = state["messages"]
    last_message = messages[-1]
    
    if not getattr(last_message, "tool_calls", None):
        return "__end__"
        
    # Check if we just received a command to execute approved tools from the CLI
    if len(messages) >= 2:
        prev = messages[-2]
        if isinstance(prev, HumanMessage) and "User approved the operation" in prev.content:
            # The CLI appended this. We need to actually execute the tools!
            # But the last message is an AIMessage with tool_calls. We can just route to tools.
            return "tools"
            
    # Check if any tool call is mutating
    for tc in last_message.tool_calls:
        if is_mutating_tool_call(tc):
            # If it's mutating, and we haven't just approved it, pause execution by going to end
            # We will add a flag to the AIMessage so the CLI knows it needs approval
            last_message.additional_kwargs["requires_approval"] = True
            return "__end__"
            
    return "tools"

def agent_node(state: AgentState):
    llm = get_llm()
    if not llm:
        return {"messages": [AIMessage(content="LLM is not configured properly.")]}
        
    messages = state["messages"]
    
    # Dynamic tool selection based on the latest human message
    user_query = ""
    history_tool_names = set()
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            if "User approved" not in msg.content and "User rejected" not in msg.content:
                user_query = msg.content
                break
        if isinstance(msg, AIMessage) and hasattr(msg, "tool_calls"):
            for tc in msg.tool_calls:
                history_tool_names.add(tc["name"])
                
    _, selected_tools = select_relevant_tools(ALL_TOOLS, user_query, max_tools=10, history_tool_names=history_tool_names)
    llm_with_tools = llm.bind_tools(selected_tools)
    
    if not any(isinstance(m, HumanMessage) for m in messages):
        return {"messages": []}
        
    # Filter out the "User approved" messages from the LLM's context to avoid confusing it
    # AND remove any AIMessages that have requires_approval=True that were left hanging
    filtered_messages = []
    for m in messages:
        if isinstance(m, HumanMessage) and ("User approved" in m.content or "User rejected" in m.content):
            continue
        filtered_messages.append(m)
        
    full_messages = [{"role": "system", "content": SYSTEM_PROMPT}] + filtered_messages
    
    response = llm_with_tools.invoke(full_messages)
    return {"messages": [response]}

# Define the graph
graph_builder = StateGraph(AgentState)
graph_builder.add_node("agent", agent_node)
graph_builder.add_node("tools", ToolNode(ALL_TOOLS))

graph_builder.add_edge(START, "agent")
graph_builder.add_conditional_edges("agent", should_continue)
graph_builder.add_edge("tools", "agent")

app_graph = graph_builder.compile()

def get_agent_graph():
    return app_graph
