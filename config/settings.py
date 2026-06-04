from pydantic import BaseModel
from dotenv import load_dotenv
import os

load_dotenv()

class Settings(BaseModel):
    app_name: str = os.getenv("APP_NAME", "Auto-Forge-MAS")
    app_env: str = os.getenv("APP_ENV", "development")

    llm_provider: str = os.getenv("LLM_PROVIDER", "ollama").lower()

    openai_api_key: str | None = os.getenv("OPENAI_API_KEY")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    ollama_model: str = os.getenv("OLLAMA_MODEL", "llama3.2:3b")

    llm_temperature: float = float(os.getenv("LLM_TEMPERATURE", "0.5"))

    embedding_provider: str = os.getenv("EMBEDDING_PROVIDER", "ollama").lower()
    openai_embedding_model: str = os.getenv("OPENAI_EMBEDDING_MODEL","text-embedding-3-small")
    ollama_embedding_model: str = os.getenv("OLLAMA_EMBEDDING_MODEL","nomic-embed-text")



settings = Settings()