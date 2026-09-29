import os
from typing import List, Dict, Any, Callable, Awaitable
from langchain_ollama import ChatOllama
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage
from .agent_tools import (
    search_solace_entity, get_entity_relationships, duplicate_solace_entity,
    update_entity_relationship, get_entity_impact, get_schema_content,
    create_solace_entity, create_solace_entity_version,
    delete_solace_entity, delete_solace_entity_version,
    manage_solace_queue, get_queue_stats, list_queues,
    get_queue_subscriptions, manage_queue_subscription, get_client_username
)

ALL_TOOLS = [
    search_solace_entity, get_entity_relationships, duplicate_solace_entity,
    update_entity_relationship, get_entity_impact, get_schema_content,
    create_solace_entity, create_solace_entity_version,
    delete_solace_entity, delete_solace_entity_version,
    manage_solace_queue, get_queue_stats, list_queues,
    get_queue_subscriptions, manage_queue_subscription, get_client_username
]

def get_llm():
    return ChatOllama(
        model=os.environ.get("OLLAMA_MODEL", "qwen3:8b"),
        base_url=os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434"),
        temperature=0.0
    )

def is_mutating_tool_call(tool_call) -> bool:
    name = tool_call.get("name", "") if isinstance(tool_call, dict) else getattr(tool_call, "name", "")
    
    # Check if the tool is generally mutating
    if name in [
        "create_solace_entity",
        "create_solace_entity_version",
        "duplicate_solace_entity",
        "update_entity_relationship",
        "delete_solace_entity",
        "delete_solace_entity_version",
    ]:
        return True
        
    # For manage_solace_queue, "get" is read-only
    if name == "manage_solace_queue":
        args = tool_call.get("args", {}) if isinstance(tool_call, dict) else getattr(tool_call, "args", {})
        return args.get("action") != "get"
        
    # For manage_queue_subscription, "list" is read-only
    if name == "manage_queue_subscription":
        args = tool_call.get("args", {}) if isinstance(tool_call, dict) else getattr(tool_call, "args", {})
        return args.get("action") != "list"
        
    return False

# We will import select_relevant_tools inside to avoid circular dependencies if any
from .tool_selector import select_relevant_tools

SYSTEM_PROMPT = """You are an autonomous AI assistant managing a Solace Event Broker and Event Portal.
You have access to a set of native tools (functions) to read and write configuration.

CRITICAL INSTRUCTION: You MUST execute these tools yourself using function calling. NEVER output CLI commands (like `manage_solace_queue --action...`) or tell the user to run them. You are the one executing the tools!

1. When asked to find an entity, ALWAYS call the `search_solace_entity` tool first to get its exact ID.
2. If you need related entities, call the `get_entity_relationships` tool with the ID you found.
3. If you need the contents of a schema, call the `get_schema_content` tool.
4. When asked to create or duplicate, always look up the parent Domain or Application first to ensure it exists and to get its ID.
5. For managing queues, ALWAYS call the `manage_solace_queue` tool. 
6. When answering, always be concise and structured. Use bullet points.
7. Never fabricate data — only report what the tools return.
8. For Create, Update, or Delete operations, the system will automatically pause and ask the user for approval. Do NOT hallucinate IDs, always search for them first.
9. NEVER tell the user how to use a tool or what steps to follow. ALWAYS execute the tool function yourself and provide the final answer directly.
"""

async def execute_agent(
    prompt: str, 
    history: List[Any], 
    approval_callback: Callable[[List[Any]], Awaitable[bool]]
) -> str:
    """
    Executes the agent loop.
    history: a list of LangChain Message objects (HumanMessage, AIMessage, etc.)
    approval_callback: an async function that takes a list of tool_calls and returns True if approved, False if rejected.
    Returns the final AI response string.
    """
    llm = get_llm()
    if not llm:
        return "Error: LLM is not configured properly."

    # Initialize messages for this run
    messages = [SystemMessage(content=SYSTEM_PROMPT)] + history
    messages.append(HumanMessage(content=prompt))

    while True:
        # 1. Dynamic Tool Selection
        user_query = prompt
        history_tool_names = set()
        for msg in reversed(messages):
            if isinstance(msg, AIMessage) and hasattr(msg, "tool_calls"):
                for tc in msg.tool_calls:
                    history_tool_names.add(tc["name"])

        _, selected_tools = select_relevant_tools(
            ALL_TOOLS, user_query, max_tools=10, history_tool_names=history_tool_names
        )
        llm_with_tools = llm.bind_tools(selected_tools)

        # 2. Call the LLM
        response = await llm_with_tools.ainvoke(messages)
        messages.append(response)

        # 3. Check if LLM wants to use tools
        if not response.tool_calls:
            # We are done, return the final content
            return response.content

        # 4. Check for mutations and ask for approval
        mutating_calls = [tc for tc in response.tool_calls if is_mutating_tool_call(tc)]
        if mutating_calls:
            is_approved = await approval_callback(mutating_calls)
            if not is_approved:
                # Inject a rejection message for all pending tools and let the LLM react
                for tc in response.tool_calls:
                    messages.append(ToolMessage(
                        tool_call_id=tc["id"],
                        name=tc["name"],
                        content='{"error": "User denied permission to execute this operation."}'
                    ))
                continue

        # 5. Execute all tools
        tool_by_name = {t.name: t for t in selected_tools}
        for tc in response.tool_calls:
            tool_func = tool_by_name.get(tc["name"])
            if tool_func:
                try:
                    # tool_func.invoke expects a dictionary of args or the tool call directly
                    result = await tool_func.ainvoke(tc["args"])
                    messages.append(ToolMessage(
                        tool_call_id=tc["id"],
                        name=tc["name"],
                        content=str(result)
                    ))
                except Exception as e:
                    messages.append(ToolMessage(
                        tool_call_id=tc["id"],
                        name=tc["name"],
                        content=f'{{"error": "{str(e)}"}}'
                    ))
            else:
                messages.append(ToolMessage(
                    tool_call_id=tc["id"],
                    name=tc["name"],
                    content='{"error": "Tool not found"}'
                ))
