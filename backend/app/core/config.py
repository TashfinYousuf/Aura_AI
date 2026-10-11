# FILE: backend/app/core/config.py

import os
from pathlib import Path
from typing import List, Any
from dotenv import load_dotenv
from pydantic import field_validator
from pydantic_settings import BaseSettings

current_dir = Path(__file__).resolve().parent
for parent in [current_dir.parents[1], current_dir.parents[2]]:
    env_file = parent / ".env"
    if env_file.exists():
        load_dotenv(env_file, override=True)
        break
else:
    load_dotenv(override=True)

class ModelRegistry:
    FAST_MODEL: str = "openai/gpt-oss-120b"
    SMART_MODEL: str = "openai/gpt-oss-120b"
    STRUCTURED_MODEL: str = "openai/gpt-oss-120b"
    SPECIALIZED_MODEL: str = "openai/gpt-oss-120b"

class Settings(BaseSettings):
    PROJECT_NAME: str = "Aura Multimodal Companion OS"
    DEBUG: bool = False

    @field_validator("DEBUG", mode="before")
    @classmethod
    def parse_debug(cls, v: Any) -> bool:
        if isinstance(v, bool):
            return v
        if isinstance(v, str):
            return v.lower() in ("true", "1", "yes", "debug", "development")
        return bool(v)
    
    # Models
    PRIMARY_CHAT_MODEL: str = ModelRegistry.SMART_MODEL
    FAST_CLASSIFIER_MODEL: str = ModelRegistry.FAST_MODEL
    FAST_MODEL: str = ModelRegistry.FAST_MODEL
    SMART_MODEL: str = ModelRegistry.SMART_MODEL
    STRUCTURED_MODEL: str = ModelRegistry.STRUCTURED_MODEL
    DEFAULT_TEMPERATURE: float = 0.65
    MAX_TOKENS: int = 400
    FALLBACK_CHAT_MODELS: List[str] = [
        "openai/gpt-oss-120b",
        "meta-llama/llama-3.3-70b-versatile",
        "openai/gpt-oss-20b"
    ]
    
    # Security & Storage
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./aura.db")
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_SERVICE_ROLE_KEY: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    
    # Firebase Auth
    FIREBASE_PROJECT_ID: str = os.getenv("FIREBASE_PROJECT_ID", "aura-companion-os")
    FIREBASE_CREDENTIALS_PATH: str = os.getenv("FIREBASE_CREDENTIALS_PATH", "")

    # API Keys
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    ELEVENLABS_API_KEY: str = os.getenv("ELEVENLABS_API_KEY", "")
    ELEVENLABS_VOICE_ID: str = os.getenv("ELEVENLABS_VOICE_ID", "EXAVITQu4vr4xnSDxMaL")  # Sarah - sweet warm young companion
    # Remote Cloud / Google Colab Stable Diffusion
    SD_REMOTE_URL: str = os.getenv("SD_REMOTE_URL", "")
    COLAB_SD_API_URL: str = os.getenv("COLAB_SD_API_URL", "")
    ENABLE_ADULT_PIPELINE: bool = True

    # CORS
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        os.getenv("FRONTEND_PRODUCTION_URL", "https://aura-companion.vercel.app")
    ]

    class Config:
        extra = "allow"

    def __getattr__(self, name: str) -> Any:
        try:
            return super().__getattr__(name)
        except AttributeError:
            if "FAST" in name or "CLASSIFIER" in name:
                return ModelRegistry.FAST_MODEL
            if "SMART" in name or "PRIMARY" in name:
                return ModelRegistry.SMART_MODEL
            if "STRUCTURED" in name:
                return ModelRegistry.STRUCTURED_MODEL
            raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

settings = Settings()
models = ModelRegistry()