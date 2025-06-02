"""
Main entry point for the Notion-Slack AI Agent system.
"""
import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from agno.agent import Agent
from agno.models.openai import OpenAI
from agno.storage.agent import AgentStorage

from src.config import Settings, get_settings
from src.tools.notion_tools import NotionTools
from src.tools.slack_tools import SlackTools
from src.api.routes import api_router
from src.services.monitoring import setup_monitoring
from src.integrations.webhook_handlers import webhook_router

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management."""
    # Startup
    logger.info("Starting Notion-Slack AI Agent...")
    settings = get_settings()
    
    # Setup monitoring
    setup_monitoring(settings)
    
    # Initialize agent
    agent = Agent(
        name="NotionSlackAgent",
        model=OpenAI(id=settings.model_id),
        tools=[NotionTools(), SlackTools()],
        storage=AgentStorage(
            table_name="agent_sessions",
            db_file="agent_storage.db"
        ),
        description="AI agent for Notion-Slack integration and automation",
        instructions=[
            "You are a helpful assistant that bridges Notion and Slack",
            "Always provide clear, actionable responses",
            "When creating tasks, include all relevant details",
            "Maintain context across conversations",
            "Follow security best practices for data handling",
            "Validate all inputs before processing"
        ],
        show_tool_calls=True,
        markdown=True
    )
    
    app.state.agent = agent
    app.state.settings = settings
    
    logger.info("Agent initialized successfully")
    yield
    
    # Shutdown
    logger.info("Shutting down Notion-Slack AI Agent...")

# Create FastAPI app
app = FastAPI(
    title="Notion-Slack AI Agent",
    description="AI-powered integration between Notion and Slack",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router, prefix="/api/v1")
app.include_router(webhook_router, prefix="/webhook")

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "notion-slack-agent",
        "version": "1.0.0"
    }

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Notion-Slack AI Agent API",
        "docs": "/docs",
        "health": "/health"
    }

def main():
    """Run the application."""
    import uvicorn
    settings = get_settings()
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=settings.port,
        reload=settings.debug
    )

if __name__ == "__main__":
    main()