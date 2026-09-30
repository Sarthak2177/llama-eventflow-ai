import asyncio
import sys

from src import config
from src.mcp_client import managed_session
from src.agent_tools import set_mcp_session, ALL_TOOLS
from src.agent import execute_agent
from langchain_core.messages import HumanMessage, AIMessage
from rich.console import Console
from rich.markdown import Markdown

console = Console()

BANNER = f"""
==========================================================================
  EventFlow AI  --  Unified CLI Mode
  Model  : {config.LLM_MODEL}
  Persona: {{persona}}
==========================================================================
  Type your question, or use a slash command:
    /help  /tools  /clear  /persona  /exit
--------------------------------------------------------------------------
"""

HELP_TEXT = """
Slash Commands:
  /help     Show this help message
  /tools    List all available Smart Router tools
  /clear    Clear the screen
  /persona  Switch persona (Admin / End User)
  /exit     Exit EventFlow AI
"""

def select_persona() -> str:
    print("\nSelect Persona:")
    print("  1. Admin     (Full read + write access)")
    print("  2. End User  (Read-only access)")
    while True:
        choice = input("\nEnter 1 or 2: ").strip()
        if choice == "1":
            return "admin"
        if choice == "2":
            return "end_user"
        print("Please enter 1 or 2.")

def persona_label(persona: str) -> str:
    return "Admin" if persona == "admin" else "End User (Read-Only)"

async def main():
    try:
        config.validate()
    except EnvironmentError as e:
        print(e)
        sys.exit(1)

    persona = select_persona()
    print(BANNER.format(persona=persona_label(persona)))
    print("[...] Connecting to Solace MCP Servers, please wait...\n")

    try:
        async with managed_session() as session:
            set_mcp_session(session)
            print(f"[OK] Connected — Smart Router Active.\n")
            history = []

            while True:
                try:
                    user_input = input("You: ").strip()
                except (EOFError, KeyboardInterrupt):
                    print("\n\nGoodbye!")
                    break

                if not user_input:
                    continue

                if user_input.lower() == "/exit":
                    print("Goodbye!")
                    break
                elif user_input.lower() == "/help":
                    print(HELP_TEXT)
                elif user_input.lower() == "/clear":
                    print("\033[2J\033[H", end="")
                    print(BANNER.format(persona=persona_label(persona)))
                elif user_input.lower() == "/persona":
                    persona = select_persona()
                    print(f"\n[OK] Switched to: {persona_label(persona)}\n")
                elif user_input.lower() == "/tools":
                    print(f"\nAvailable Tools ({len(ALL_TOOLS)} total):")
                    for i, t in enumerate(ALL_TOOLS, 1):
                        print(f"  {i:>2}. {t.name:<45} {t.description[:60]}")
                    print()
                else:
                    print("\n[...] Thinking...\n")
                    try:
                        final_answer = await execute_agent(user_input, history, persona)
                        
                        print("EventFlow AI:")
                        console.print(Markdown(final_answer))
                        print()
                        
                        # Add to history to maintain conversational context
                        history.append(HumanMessage(content=user_input))
                        history.append(AIMessage(content=final_answer))
                        history = history[-10:] # Keep only the last 10 messages to prevent bloat
                        
                        print("-" * 72)
                    except Exception as exc:
                        print(f"[ERROR] {exc}\n")

    except Exception as exc:
        print(f"\n[ERROR] Failed to connect to Solace MCP Server: {exc}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
