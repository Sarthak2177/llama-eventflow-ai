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

def should_continue(state: AgentState) -> Literal["tools", "human_approval", "__end__"]:
    messages = state["messages"]
    last_message = messages[-1]
    
    if not getattr(last_message, "tool_calls", None):
        return "__end__"
        
    # If the user explicitly approved the operation in the previous turn, bypass the check and execute
    if len(messages) >= 2:
        prev_msg = messages[-2]
        if isinstance(prev_msg, HumanMessage) and "User approved the operation" in prev_msg.content:
            return "tools"
    
    # Check if any tool call is mutating
    for tc in last_message.tool_calls:
        if is_mutating_tool_call(tc):
            return "human_approval"
            
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
            user_query = msg.content
            break
        if isinstance(msg, AIMessage) and hasattr(msg, "tool_calls"):
            for tc in msg.tool_calls:
                history_tool_names.add(tc["name"])
                
    # Use Gemma's dynamic tool selector
    # It returns (ollama_tools, mcp_tools) where mcp_tools are our selected LangChain tools
    _, selected_tools = select_relevant_tools(ALL_TOOLS, user_query, max_tools=10, history_tool_names=history_tool_names)
    
    # Bind only the dynamically selected tools
    llm_with_tools = llm.bind_tools(selected_tools)
    
    if not any(isinstance(m, HumanMessage) for m in messages):
        # Should have a human message
        return {"messages": []}
        
    # Inject system prompt
    full_messages = [{"role": "system", "content": SYSTEM_PROMPT}] + [m for m in messages]
    
    response = llm_with_tools.invoke(full_messages)
    return {"messages": [response]}


def human_approval_node(state: AgentState):
    # This node is reached when a mutating tool is called.
    # In LangGraph, we can use an interrupt. Here we just return a message asking for approval,
    # or rely on the host application to handle the interrupt.
    # For this architecture, we will yield a special message that the UI/CLI will catch.
    last_message = state["messages"][-1]
    tool_calls = getattr(last_message, "tool_calls", [])
    
    msg = f"I need your approval to execute the following operations:\n"
    for tc in tool_calls:
        msg += f"- {tc['name']} with args: {tc['args']}\n"
    msg += "\nPlease type 'approve' to proceed or 'reject' to cancel."
    
    return {"messages": [AIMessage(content=msg, additional_kwargs={"requires_approval": True, "pending_tool_calls": tool_calls})]}


# Define the graph
graph_builder = StateGraph(AgentState)
graph_builder.add_node("agent", agent_node)
graph_builder.add_node("tools", ToolNode(ALL_TOOLS))
graph_builder.add_node("human_approval", human_approval_node)

graph_builder.add_edge(START, "agent")
graph_builder.add_conditional_edges("agent", should_continue)
graph_builder.add_edge("tools", "agent")
# Human approval goes to END to wait for user input. The app will inject a ToolMessage or approval message.
graph_builder.add_edge("human_approval", END) 

app_graph = graph_builder.compile()

def get_agent_graph():
    return app_graph
