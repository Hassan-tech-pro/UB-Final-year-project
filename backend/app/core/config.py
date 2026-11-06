import os
from pathlib import Path
from typing import Union, Any
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent
PROJECT_ROOT = BASE_DIR.parent

class Settings(BaseSettings):
    # App
    PROJECT_NAME: str = "Agentic AI Task Automation & Verification System"
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    PORT: int = 8000
    HOST: str = "0.0.0.0"
    CORS_ORIGINS: Union[list[str], str] = ["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173", "http://127.0.0.1:3000"]

    # Storage Paths (Guaranteed absolute)
    WORKSPACE_DIR: Path = (BASE_DIR / "storage" / "workspace").resolve()
    UPLOAD_DIR: Path = (BASE_DIR / "storage" / "uploads").resolve()
    ARTIFACT_DIR: Path = (BASE_DIR / "storage" / "artifacts").resolve()
    SAMPLE_DATA_DIR: Path = (PROJECT_ROOT / "sample_data").resolve()
    DATABASE_PATH: Path = (BASE_DIR / "storage" / "agent_system.db").resolve()

    # Execution limits
    MAX_TASK_RETRIES: int = 3
    TASK_TIMEOUT_SECONDS: int = 120
    WORKFLOW_TIMEOUT_SECONDS: int = 600
    MAX_UPLOAD_SIZE_MB: int = 50

    # LLM Settings
    LLM_PROVIDER: str = "mock"
    MODEL_NAME: str = "gemini-2.5-flash"
    GEMINI_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""

    # Allowed Upload Extensions
    ALLOWED_EXTENSIONS: set[str] = {".pdf", ".docx", ".xlsx", ".xls", ".csv", ".txt", ".json"}

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, list[str]]) -> list[str]:
        if isinstance(v, str):
            if v.startswith("[") and v.endswith("]"):
                import json
                try:
                    return json.loads(v)
                except Exception:
                    pass
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, list):
            return v
        return ["*"]

    @field_validator("WORKSPACE_DIR", "UPLOAD_DIR", "ARTIFACT_DIR", "SAMPLE_DATA_DIR", "DATABASE_PATH", mode="before")
    @classmethod
    def assemble_absolute_paths(cls, v: Any) -> Path:
        if isinstance(v, Path):
            return v.resolve()
        if isinstance(v, str):
            p = Path(v)
            if not p.is_absolute():
                return (BASE_DIR / p).resolve()
            return p.resolve()
        return v

    model_config = SettingsConfigDict(
        env_file=(str(PROJECT_ROOT / ".env"), str(BASE_DIR / ".env")),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    def init_directories(self):
        """Ensure all required workspace directories exist safely."""
        self.WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)
        self.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        self.ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
        self.SAMPLE_DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)

settings = Settings()
settings.init_directories()
