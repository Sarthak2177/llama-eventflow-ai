from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import uuid

from contextlib import AsyncExitStack, asynccontextmanager
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage

from src import config
from src.mcp_client import managed_session
from src.agent_tools import set_mcp_session
from src.agent import get_agent_graph

# Global variable to hold our compiled LangGraph
app_graph = get_agent_graph()
conversation_store = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Initializing MCP Client...")
    try:
        async with managed_session() as session:
            set_mcp_session(session)
            print("EventFlow AI MCP session connected successfully!")
            yield
    except Exception as e:
        print(f"Failed to start MCP Client: {e}")
        yield

app = FastAPI(
    title="EventFlow AI Orchestrator",
    description="Backend AI layer for interpreting natural language and interacting with Solace MCP servers.",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    approval: Optional[str] = None

class ToolCall(BaseModel):
    tool: str
    args: dict

class ChatResponse(BaseModel):
    reply: str
    model_used: str
    session_id: str
    tools_used: List[ToolCall]
    requires_approval: bool = False

class SessionResponse(BaseModel):
    session_id: str

@app.get("/ui", response_class=HTMLResponse)
def serve_ui():
    """Serves the Backstage EventFlow Assistant prototype UI."""
    return FileResponse("index.html")

@app.post("/session", response_model=SessionResponse)
def new_session():
    """Create a new conversation session for multi-turn chat."""
    sid = str(uuid.uuid4())
    conversation_store[sid] = []
    return SessionResponse(session_id=sid)

@app.post("/chat", response_model=ChatResponse)
async def chat_with_llm(request: ChatRequest):
    if not app_graph:
        raise HTTPException(status_code=503, detail="Agent graph is not initialized.")
        
    session_id = request.session_id or str(uuid.uuid4())
    if session_id not in conversation_store:
        conversation_store[session_id] = []
        
    history = conversation_store[session_id]
    
    if request.approval:
        if request.approval.lower() == "approve":
            # Just say approved, the graph will continue since we don't have checkpointing set up, 
            # in a real LangGraph setup we would resume the thread.
            # Here we just pass the approval to the LLM to continue.
            history.append(HumanMessage(content="User approved the operation. Please proceed with the pending tool calls."))
        else:
            history.append(HumanMessage(content="User rejected the operation. Do not proceed. Let the user know it was cancelled."))
    else:
        history.append(HumanMessage(content=request.message))
        
    inputs = {"messages": history, "session_id": session_id}
    
    try:
        result = await app_graph.ainvoke(inputs, config={"recursion_limit": 50})
        
        tools_used = []
        requires_approval = False
        reply = ""
        
        last_message = result["messages"][-1]
        
        for msg in result["messages"]:
            if getattr(msg, "tool_calls", None):
                for tc in msg.tool_calls:
                    tools_used.append(ToolCall(tool=tc["name"], args=tc["args"]))
                    
        if isinstance(last_message, AIMessage):
            reply = last_message.content
            if last_message.additional_kwargs.get("requires_approval"):
                requires_approval = True
                
        # Update history
        conversation_store[session_id] = result["messages"][-20:]
        
        return ChatResponse(
            reply=reply,
            model_used=config.LLM_MODEL,
            session_id=session_id,
            tools_used=tools_used,
            requires_approval=requires_approval
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000)
