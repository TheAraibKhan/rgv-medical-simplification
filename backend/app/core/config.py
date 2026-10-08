from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path


class Settings(BaseSettings):
    app_env: str = "development"
    app_mode: str = "demo"
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000
    frontend_origin: str = "http://localhost:3000"

    database_url: str = "postgresql+psycopg://rgv:rgv@localhost:5432/rgv"
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "medlineplus"

    llm_provider: str = "demo"
    vllm_base_url: str = "http://localhost:8001/v1"
    vllm_model: str = ""
    vllm_api_key: str = "local"

    verifier_provider: str = "heuristic"
    verifier_model: str = ""
    verifier_threshold: float = 0.80

    medlineplus_snapshot_date: str = ""
    medlineplus_corpus_path: Path = Path("data/medlineplus/snapshot.jsonl")
    default_top_k: int = 3
    max_correction_attempts: int = 2
    max_upload_bytes: int = 20 * 1024 * 1024

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
