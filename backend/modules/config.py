import os
from typing import Optional, Dict, Any

LLM_CONFIG = {
    "provider": os.getenv("LLM_PROVIDER", "openai"),
    "model": os.getenv("LLM_MODEL", "gpt-4o-mini"),
    "temperature": float(os.getenv("LLM_TEMPERATURE", "0.7")),
    "max_tokens": int(os.getenv("LLM_MAX_TOKENS", "2000")),
    "ollama_url": os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
}

llm_status: Dict[str, Any] = {"connected": False, "provider": "", "model": "", "error": ""}

def get_llm_config() -> Dict[str, str]:
    return LLM_CONFIG.copy()

def get_llm_status() -> Dict[str, Any]:
    return llm_status.copy()

def set_llm_status(status: Dict[str, Any]):
    global llm_status
    llm_status = status
