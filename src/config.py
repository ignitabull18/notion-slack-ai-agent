"""
Configuration management for the Notion-Slack AI Agent.
"""
import os
from typing import List, Optional
from functools import lru_cache
from pydantic_settings import BaseSettings
from pydantic import Field, validator

class Settings(BaseSettings):
    """Application settings."""
    
    # Application
    app_name: str = Field(default="notion-slack-agent", env="APP_NAME")
    app_version: str = Field(default="1.0.0", env="APP_VERSION")
    port: int = Field(default=8000, env="PORT")
    debug: bool = Field(default=False, env="DEBUG")
    environment: str = Field(default="production", env="ENVIRONMENT")
    
    # AI Model
    openai_api_key: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    anthropic_api_key: Optional[str] = Field(default=None, env="ANTHROPIC_API_KEY")
    model_provider: str = Field(default="openai", env="MODEL_PROVIDER")
    model_id: str = Field(default="gpt-4", env="MODEL_ID")
    model_temperature: float = Field(default=0.7, env="MODEL_TEMPERATURE")
    model_max_tokens: int = Field(default=2000, env="MODEL_MAX_TOKENS")
    
    # Notion
    notion_integration_token: str = Field(..., env="NOTION_INTEGRATION_TOKEN")
    notion_workspace_id: str = Field(..., env="NOTION_WORKSPACE_ID")
    notion_webhook_secret: Optional[str] = Field(default=None, env="NOTION_WEBHOOK_SECRET")
    notion_api_version: str = Field(default="2022-06-28", env="NOTION_API_VERSION")
    
    # Slack
    slack_bot_token: str = Field(..., env="SLACK_BOT_TOKEN")
    slack_app_token: str = Field(..., env="SLACK_APP_TOKEN")
    slack_signing_secret: str = Field(..., env="SLACK_SIGNING_SECRET")
    slack_client_id: Optional[str] = Field(default=None, env="SLACK_CLIENT_ID")
    slack_client_secret: Optional[str] = Field(default=None, env="SLACK_CLIENT_SECRET")
    
    # Database
    database_url: str = Field(
        default="postgresql://user:password@localhost:5432/notion_slack_agent",
        env="DATABASE_URL"
    )
    redis_url: str = Field(default="redis://localhost:6379", env="REDIS_URL")
    
    # Vector Store
    qdrant_url: str = Field(default="http://localhost:6333", env="QDRANT_URL")
    qdrant_api_key: Optional[str] = Field(default=None, env="QDRANT_API_KEY")
    supabase_url: Optional[str] = Field(default=None, env="SUPABASE_URL")
    supabase_key: Optional[str] = Field(default=None, env="SUPABASE_KEY")
    
    # Security
    api_secret_key: str = Field(..., env="API_SECRET_KEY")
    jwt_secret_key: str = Field(..., env="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", env="JWT_ALGORITHM")
    jwt_expiration_hours: int = Field(default=24, env="JWT_EXPIRATION_HOURS")
    
    # CORS
    cors_origins: List[str] = Field(
        default=["http://localhost:3000"],
        env="CORS_ORIGINS"
    )
    
    # Rate Limiting
    rate_limit_enabled: bool = Field(default=True, env="RATE_LIMIT_ENABLED")
    rate_limit_default: str = Field(default="1000/hour", env="RATE_LIMIT_DEFAULT")
    rate_limit_burst: int = Field(default=50, env="RATE_LIMIT_BURST")
    
    # Monitoring
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    prometheus_enabled: bool = Field(default=True, env="PROMETHEUS_ENABLED")
    prometheus_port: int = Field(default=9090, env="PROMETHEUS_PORT")
    sentry_dsn: Optional[str] = Field(default=None, env="SENTRY_DSN")
    
    # Webhooks
    webhook_base_url: Optional[str] = Field(default=None, env="WEBHOOK_BASE_URL")
    
    @validator("cors_origins", pre=True)
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v
    
    @validator("model_provider")
    def validate_model_provider(cls, v, values):
        if v == "openai" and not values.get("openai_api_key"):
            raise ValueError("OpenAI API key required when using OpenAI provider")
        elif v == "anthropic" and not values.get("anthropic_api_key"):
            raise ValueError("Anthropic API key required when using Anthropic provider")
        return v
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()

def get_database_url() -> str:
    """Get database URL."""
    return get_settings().database_url

def get_redis_url() -> str:
    """Get Redis URL."""
    return get_settings().redis_url