import os
from dotenv import load_dotenv

load_dotenv()

SOLACE_API_TOKEN = os.getenv("SOLACE_API_TOKEN", "")
SOLACE_API_BASE_URL = os.getenv("SOLACE_API_BASE_URL", "https://api.solace.cloud")
LLM_MODEL = os.getenv("LLM_MODEL", "qwen3:8b")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "http://localhost:11434")

def validate():
    pass
