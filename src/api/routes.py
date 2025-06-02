"""
API routes for the Notion-Slack AI Agent.
"""
from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
import asyncio
import logging

from src.config import get_settings
from src.tools.notion_tools import NotionTools
from src.tools.slack_tools import SlackTools

logger = logging.getLogger(__name__)
security = HTTPBearer()

# Create the main API router
api_router = APIRouter()

# Pydantic models for request/response
class AgentRequest(BaseModel):
    message: str
    channel_id: Optional[str] = None
    user_id: Optional[str] = None
    thread_ts: Optional[str] = None

class AgentResponse(BaseModel):
    success: bool
    response: str
    message_ts: Optional[str] = None
    error: Optional[str] = None

class NotionPageRequest(BaseModel):
    database_id: str
    title: str
    properties: Dict[str, Any] = {}

class SlackMessageRequest(BaseModel):
    channel: str
    text: str
    blocks: Optional[List[Dict]] = None
    thread_ts: Optional[str] = None

# Authentication dependency
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Validate API key authentication."""
    settings = get_settings()
    if credentials.credentials != settings.api_secret_key:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return credentials.credentials

@api_router.get("/status")
async def get_agent_status():
    """Get the current status of the AI agent."""
    return {
        "status": "active",
        "service": "notion-slack-agent",
        "version": "1.0.0",
        "components": {
            "notion_tools": "ready",
            "slack_tools": "ready",
            "agent": "ready"
        }
    }

@api_router.post("/chat", response_model=AgentResponse)
async def chat_with_agent(
    request: AgentRequest,
    current_user: str = Depends(get_current_user),
    fastapi_request: Request = None
):
    """Send a message to the AI agent and get a response."""
    try:
        # Get the agent from the FastAPI app state
        agent = fastapi_request.app.state.agent
        
        # Process the message with the agent
        response = agent.run(request.message)
        
        # If channel_id is provided, send response to Slack
        message_ts = None
        if request.channel_id:
            slack_tools = SlackTools()
            slack_response = await slack_tools.send_message(
                channel=request.channel_id,
                text=response.content,
                thread_ts=request.thread_ts
            )
            if slack_response.get("success"):
                message_ts = slack_response.get("ts")
        
        return AgentResponse(
            success=True,
            response=response.content,
            message_ts=message_ts
        )
    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}")
        return AgentResponse(
            success=False,
            response="I encountered an error processing your request.",
            error=str(e)
        )

@api_router.get("/notion/databases")
async def list_notion_databases(
    current_user: str = Depends(get_current_user)
):
    """List accessible Notion databases."""
    try:
        notion_tools = NotionTools()
        # Note: Notion API doesn't have a direct "list databases" endpoint
        # This would need to be implemented using search or pre-configured database IDs
        return {
            "success": True,
            "message": "Use search endpoint to find databases",
            "databases": []
        }
    except Exception as e:
        logger.error(f"Error listing databases: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/notion/pages")
async def create_notion_page(
    request: NotionPageRequest,
    current_user: str = Depends(get_current_user)
):
    """Create a new page in a Notion database."""
    try:
        notion_tools = NotionTools()
        result = notion_tools.create_page(
            parent_database_id=request.database_id,
            title=request.title,
            properties=request.properties
        )
        return result
    except Exception as e:
        logger.error(f"Error creating Notion page: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/notion/pages/{page_id}")
async def get_notion_page(
    page_id: str,
    current_user: str = Depends(get_current_user)
):
    """Get a specific Notion page."""
    try:
        notion_tools = NotionTools()
        result = notion_tools.get_page(page_id)
        return result
    except Exception as e:
        logger.error(f"Error getting Notion page: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/notion/search")
async def search_notion(
    query: str,
    filter_type: Optional[str] = None,
    current_user: str = Depends(get_current_user)
):
    """Search Notion workspace."""
    try:
        notion_tools = NotionTools()
        results = notion_tools.search_pages(query, filter_type)
        return {
            "success": True,
            "results": results
        }
    except Exception as e:
        logger.error(f"Error searching Notion: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/slack/channels")
async def list_slack_channels(
    types: str = "public_channel,private_channel",
    current_user: str = Depends(get_current_user)
):
    """List accessible Slack channels."""
    try:
        slack_tools = SlackTools()
        channels = await slack_tools.list_channels(types=types)
        return {
            "success": True,
            "channels": channels
        }
    except Exception as e:
        logger.error(f"Error listing Slack channels: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/slack/messages")
async def send_slack_message(
    request: SlackMessageRequest,
    current_user: str = Depends(get_current_user)
):
    """Send a message to a Slack channel."""
    try:
        slack_tools = SlackTools()
        result = await slack_tools.send_message(
            channel=request.channel,
            text=request.text,
            blocks=request.blocks,
            thread_ts=request.thread_ts
        )
        return result
    except Exception as e:
        logger.error(f"Error sending Slack message: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/slack/channels/{channel_id}/info")
async def get_slack_channel_info(
    channel_id: str,
    current_user: str = Depends(get_current_user)
):
    """Get information about a specific Slack channel."""
    try:
        slack_tools = SlackTools()
        result = await slack_tools.get_channel_info(channel_id)
        return result
    except Exception as e:
        logger.error(f"Error getting Slack channel info: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/slack/users/{user_id}")
async def get_slack_user_info(
    user_id: str,
    current_user: str = Depends(get_current_user)
):
    """Get information about a specific Slack user."""
    try:
        slack_tools = SlackTools()
        result = await slack_tools.get_user_info(user_id)
        return result
    except Exception as e:
        logger.error(f"Error getting Slack user info: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/workflows/sync")
async def trigger_notion_slack_sync(
    database_id: str,
    channel_id: str,
    current_user: str = Depends(get_current_user)
):
    """Trigger a sync between a Notion database and Slack channel."""
    try:
        # This would implement the core sync workflow
        # For now, we'll return a placeholder response
        return {
            "success": True,
            "message": f"Sync triggered between database {database_id} and channel {channel_id}",
            "workflow_id": f"sync_{database_id}_{channel_id}"
        }
    except Exception as e:
        logger.error(f"Error triggering sync: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/metrics")
async def get_metrics(
    current_user: str = Depends(get_current_user)
):
    """Get system metrics and performance data."""
    try:
        # This would return actual metrics in a production system
        return {
            "success": True,
            "metrics": {
                "uptime": "24h",
                "requests_processed": 1234,
                "notion_api_calls": 456,
                "slack_api_calls": 789,
                "agent_responses": 321,
                "errors": 12
            }
        }
    except Exception as e:
        logger.error(f"Error getting metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))
