import asyncio
from src.agent import get_agent_graph
from src.mcp_client import managed_session
from src.agent_tools import set_mcp_session
from langchain_core.messages import HumanMessage, AIMessage
import sys

PROMPTS = [
    "Show me all Event API Products currently available for the Airport domain.",
    "Which Event APIs are included in the Flight Information Event API Product?",
    "Show me all applications consuming events from the Flight Information API.",
    "Create a new version of the Flight Information Event API based on the current version.",
    "Duplicate the NOTAM Event API Product and name the new product NOTAMv2.",
    "Add the AircraftPosition event to the new version of the Surveillance Event API.",
    "Show me Event APIs that reference schemas that are not using their latest version.",
    "Which Event API Products will be affected if the FlightStatus event is modified?",
    "Show me all Event API Products associated with application domain Airport Operations.",
    "Add latest version of 'Surveillance' Event API in 'Flight Information' Event API Product"
]

async def run_test(prompt_idx: int = None):
    async with managed_session() as session:
        set_mcp_session(session)
        app_graph = get_agent_graph()
        
        # If an index is provided, only run that specific prompt
        prompts_to_run = enumerate(PROMPTS, 1)
        if prompt_idx is not None:
            if prompt_idx < 1 or prompt_idx > len(PROMPTS):
                print(f"Error: Prompt index {prompt_idx} out of range.")
                return
            prompts_to_run = [(prompt_idx, PROMPTS[prompt_idx - 1])]
        
        for i, prompt in prompts_to_run:
            print(f"\n=======================================================")
            print(f"PROMPT {i}: {prompt}")
            print(f"=======================================================")
            
            history = [HumanMessage(content=prompt)]
            try:
                result = await app_graph.ainvoke({"messages": history, "session_id": f"test-{i}"}, config={"recursion_limit": 50})
                
                last_message = result["messages"][-1]
                if isinstance(last_message, AIMessage):
                    print(f"\n[AI RESPONSE]\n{last_message.content}\n")
                    
                    if last_message.additional_kwargs.get("requires_approval"):
                        print(f"\n[SYSTEM: Auto-approving mutating operation]")
                        
                        history = list(result["messages"])
                        history.append(HumanMessage(content="User approved the operation. Please proceed."))
                        
                        result2 = await app_graph.ainvoke({"messages": history, "session_id": f"test-{i}"})
                        
                        last_message2 = result2["messages"][-1]
                        if isinstance(last_message2, AIMessage):
                            print(f"\n[AI POST-APPROVAL RESPONSE]\n{last_message2.content}\n")
                            
            except Exception as e:
                print(f"\n[ERROR]\n{e}\n")

if __name__ == "__main__":
    idx = int(sys.argv[1]) if len(sys.argv) > 1 else None
    asyncio.run(run_test(idx))
