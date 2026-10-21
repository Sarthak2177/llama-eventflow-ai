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
from src.agent import execute_agent

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
    session_id = request.session_id or str(uuid.uuid4())
    if session_id not in conversation_store:
        conversation_store[session_id] = []
        
    history = conversation_store[session_id]
    
    # Handle approval logic by modifying the prompt
    prompt = request.message
    if request.approval:
        if request.approval.lower() == "approve":
            prompt = "User approved the operation. Please proceed."
        else:
            prompt = "User rejected the operation. Do not proceed."
            
    try:
        # Execute the agent loop
        reply, new_messages = await execute_agent(prompt=prompt, history=history, persona="admin")
        
        # Update history with this turn
        history.extend(new_messages)
        
        # Keep only the last 20 messages to prevent context bloat
        conversation_store[session_id] = history[-20:]
        
        return ChatResponse(
            reply=reply,
            model_used=getattr(config, "LLM_MODEL", "llama3.1:8b"),
            session_id=session_id,
            tools_used=[], # execute_agent handles tools internally
            requires_approval=False
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
