"""
Application configuration file.

This file loads environment variables from the .env file.

Important:
The .env file must control the default LLM model.
llm_schema.py should only define API request/response shapes.
"""

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


# This finds the backend root folder:
# services/agentic_service/
BASE_DIR = Path(__file__).resolve().parents[2]

# This points directly to:
# services/agentic_service/.env
ENV_FILE_PATH = BASE_DIR / ".env"


class Settings(BaseSettings):
    APP_NAME: str = "AutoForge Agentic SDLC Backend"
    APP_ENV: str = "development"
    APP_VERSION: str = "0.1.0"

    API_PREFIX: str = "/api/v1"
    OUTPUT_DIR: str = "outputs"

    # LLM settings
    DEFAULT_LLM_PROVIDER: str = "ollama"
    DEFAULT_LLM_MODEL: str = "llama4"  # This is just a placeholder. The real default model must come from .env.
    OLLAMA_BASE_URL: str = "http://localhost:11434"

    OPENAI_API_KEY: str | None = None
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    OPENAI_MODEL: str = "gpt-4o-mini"

    LLM_TEMPERATURE: float = 0.1
    LLM_MAX_TOKENS: int = 4096
    LLM_TIMEOUT_SECONDS: int = 320
    LLM_STREAMING_ENABLED: bool = True
    # MongoDB connection URI.
    # For local MongoDB: mongodb://localhost:27017
    # For MongoDB Atlas: mongodb+srv://username:password@cluster.mongodb.net
    MONGODB_URI: str = "mongodb://localhost:27017"

    # MongoDB database name used by AutoForge MAS.
    MONGODB_DATABASE: str = "autoforge_mas"
    # PlantUML configuration.
    # This is used by Architecture Agent to render use case diagrams.
    PLANTUML_JAR_PATH: str = "tools/plantuml.jar"

        # -----------------------------
    # Domain Agent RAG Settings
    # -----------------------------

    # Folder where domain knowledge files are stored.
    # Example:
    # knowledge_base/ecommerce/authentication.md
    # knowledge_base/lms/enrollment.md
    DOMAIN_KNOWLEDGE_BASE_DIR: str = "knowledge_base"

    # Folder where ChromaDB stores vector data.
    CHROMA_PERSIST_DIR: str = "vector_db/chroma"

    # Embedding model used to convert chunks into vectors.
    DOMAIN_EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"

    # Size of each text chunk.
    DOMAIN_CHUNK_SIZE: int = 900

    # Overlap between chunks so meaning is not lost between chunk boundaries.
    DOMAIN_CHUNK_OVERLAP: int = 150

    # Number of chunks retrieved for each Domain Agent run.
    DOMAIN_TOP_K: int = 6

    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE_PATH),
        env_file_encoding="utf-8"
    )


settings = Settings()