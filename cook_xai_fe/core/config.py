import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """Validated application settings loaded from environment / .env file."""
    GITHUB_TOKEN: str = ""
    GITHUB_CLIENT_ID: str = ""
    GITHUB_CLIENT_SECRET: str = ""
    
    WEBHOOK_SECRET: str  # Required — no insecure fallback
    
    # Needs to be a publicly accessible URL (ngrok, render, etc) for GitHub webhooks
    BACKEND_PUBLIC_URL: str = "http://127.0.0.1:8000"

    MONGO_URI: str = ""

    # Derived paths (not from env)
    BASE_DIR: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    @property
    def MODELS_DIR(self) -> str:
        return os.path.join(self.BASE_DIR, "models")

    @property
    def MODEL_PATH(self) -> str:
        return os.path.join(self.MODELS_DIR, "jit_risk_model.pkl")

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()