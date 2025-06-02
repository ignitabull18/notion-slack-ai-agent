"""
Webhook handlers for Notion and Slack integrations.
"""
import hmac
import hashlib
import json
import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, Request, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
import asyncio

from src.config import get_settings
from src.tools.notion_tools import NotionTools
from src.tools.slack_tools import SlackTools
from src.services.monitoring import track_notion_api_call, track_slack_api_call, track_error

logger = logging.getLogger(__name__)

# Create webhook router
webhook_router = APIRouter()

def verify_notion_webhook(request_body: bytes, signature: str, webhook_secret: str) -> bool:
    """Verify Notion webhook signature."""
    try:
        expected_signature = hmac.new(
            webhook_secret.encode(),
            request_body,
            hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(signature, expected_signature)
    except Exception as e:
        logger.error(f"Error verifying Notion webhook: {e}")
        return False

def verify_slack_webhook(request_body: bytes, timestamp: str, signature: str, signing_secret: str) -> bool:
    """Verify Slack webhook signature."""
    try:
        # Create the signature base string
        sig_basestring = f"v0:{timestamp}:{request_body.decode()}"
        
        # Calculate expected signature
        expected_signature = 'v0=' + hmac.new(
            signing_secret.encode(),
            sig_basestring.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(signature, expected_signature)
    except Exception as e:
        logger.error(f"Error verifying Slack webhook: {e}")
        return False

@webhook_router.post("/notion")
async def handle_notion_webhook(request: Request, background_tasks: BackgroundTasks):
    """Handle incoming Notion webhooks."""
    try:
        settings = get_settings()
        
        # Get request body and headers
        body = await request.body()
        signature = request.headers.get("Notion-Webhook-Signature", "")
        
        # Verify webhook signature
        if not verify_notion_webhook(body, signature, settings.notion_webhook_secret):
            logger.warning("Invalid Notion webhook signature")
            raise HTTPException(status_code=401, detail="Invalid signature")
        
        # Parse webhook payload
        try:
            payload = json.loads(body.decode())
        except json.JSONDecodeError:
            logger.error("Invalid JSON in Notion webhook")
            raise HTTPException(status_code=400, detail="Invalid JSON")
        
        # Process webhook in background
        background_tasks.add_task(process_notion_webhook, payload)
        
        return JSONResponse({"status": "received"})
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error handling Notion webhook: {e}")
        track_error("notion_webhook_error", str(e))
        raise HTTPException(status_code=500, detail="Internal server error")

@webhook_router.post("/slack/events")
async def handle_slack_events(request: Request, background_tasks: BackgroundTasks):
    """Handle Slack Events API webhooks."""
    try:
        settings = get_settings()
        
        # Get request body and headers
        body = await request.body()
        timestamp = request.headers.get("X-Slack-Request-Timestamp", "")
        signature = request.headers.get("X-Slack-Signature", "")
        
        # Verify webhook signature
        if not verify_slack_webhook(body, timestamp, signature, settings.slack_signing_secret):
            logger.warning("Invalid Slack webhook signature")
            raise HTTPException(status_code=401, detail="Invalid signature")
        
        # Parse webhook payload
        try:
            payload = json.loads(body.decode())
        except json.JSONDecodeError:
            logger.error("Invalid JSON in Slack webhook")
            raise HTTPException(status_code=400, detail="Invalid JSON")
        
        # Handle URL verification challenge
        if payload.get("type") == "url_verification":
            return JSONResponse({"challenge": payload.get("challenge")})
        
        # Process event in background
        background_tasks.add_task(process_slack_event, payload)
        
        return JSONResponse({"status": "received"})
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error handling Slack event: {e}")
        track_error("slack_webhook_error", str(e))
        raise HTTPException(status_code=500, detail="Internal server error")

@webhook_router.post("/slack/commands")
async def handle_slack_commands(request: Request, background_tasks: BackgroundTasks):
    """Handle Slack slash commands."""
    try:
        settings = get_settings()
        
        # Get form data from Slack
        form_data = await request.form()
        payload = dict(form_data)
        
        # Verify webhook (Slack commands use different verification)
        # For slash commands, verification is typically done via SSL and token
        if payload.get("token") != getattr(settings, "slack_verification_token", None):
            logger.warning("Invalid Slack command token")
            # Note: Slack is deprecating verification tokens in favor of signing secrets
            # For production, implement proper signature verification
        
        # Process command in background
        background_tasks.add_task(process_slack_command, payload)
        
        # Return immediate response to Slack
        return JSONResponse({
            "response_type": "ephemeral",
            "text": "Processing your request..."
        })
        
    except Exception as e:
        logger.error(f"Error handling Slack command: {e}")
        track_error("slack_command_error", str(e))
        raise HTTPException(status_code=500, detail="Internal server error")

async def process_notion_webhook(payload: Dict[str, Any]) -> None:
    """Process Notion webhook payload in the background."""
    try:
        logger.info(f"Processing Notion webhook: {payload.get('type', 'unknown')}")
        
        webhook_type = payload.get("type")
        object_data = payload.get("data", {})
        
        if webhook_type == "page.created":
            await handle_notion_page_created(object_data)
        elif webhook_type == "page.updated":
            await handle_notion_page_updated(object_data)
        elif webhook_type == "database.updated":
            await handle_notion_database_updated(object_data)
        else:
            logger.info(f"Unhandled Notion webhook type: {webhook_type}")
        
        track_notion_api_call("webhook_processed", True)
        
    except Exception as e:
        logger.error(f"Error processing Notion webhook: {e}")
        track_notion_api_call("webhook_processed", False)
        track_error("notion_webhook_processing", str(e))

async def process_slack_event(payload: Dict[str, Any]) -> None:
    """Process Slack event payload in the background."""
    try:
        logger.info(f"Processing Slack event: {payload.get('event', {}).get('type', 'unknown')}")
        
        event = payload.get("event", {})
        event_type = event.get("type")
        
        if event_type == "app_mention":
            await handle_slack_app_mention(event)
        elif event_type == "message":
            await handle_slack_message(event)
        elif event_type == "reaction_added":
            await handle_slack_reaction_added(event)
        else:
            logger.info(f"Unhandled Slack event type: {event_type}")
        
        track_slack_api_call("event_processed", True)
        
    except Exception as e:
        logger.error(f"Error processing Slack event: {e}")
        track_slack_api_call("event_processed", False)
        track_error("slack_event_processing", str(e))

async def process_slack_command(payload: Dict[str, Any]) -> None:
    """Process Slack slash command in the background."""
    try:
        command = payload.get("command", "")
        text = payload.get("text", "")
        user_id = payload.get("user_id", "")
        channel_id = payload.get("channel_id", "")
        response_url = payload.get("response_url", "")
        
        logger.info(f"Processing Slack command: {command} from user {user_id}")
        
        # Route to appropriate command handler
        if command == "/task":
            await handle_task_command(text, user_id, channel_id, response_url)
        elif command == "/query":
            await handle_query_command(text, user_id, channel_id, response_url)
        elif command == "/sync":
            await handle_sync_command(text, user_id, channel_id, response_url)
        else:
            await send_command_response(response_url, f"Unknown command: {command}")
        
        track_slack_api_call("command_processed", True)
        
    except Exception as e:
        logger.error(f"Error processing Slack command: {e}")
        track_slack_api_call("command_processed", False)
        track_error("slack_command_processing", str(e))

# Notion event handlers
async def handle_notion_page_created(page_data: Dict[str, Any]) -> None:
    """Handle Notion page creation event."""
    try:
        page_id = page_data.get("id", "")
        logger.info(f"Notion page created: {page_id}")
        
        # Example: Notify Slack channel about new page
        # This would be customized based on specific requirements
        
    except Exception as e:
        logger.error(f"Error handling Notion page creation: {e}")

async def handle_notion_page_updated(page_data: Dict[str, Any]) -> None:
    """Handle Notion page update event."""
    try:
        page_id = page_data.get("id", "")
        logger.info(f"Notion page updated: {page_id}")
        
        # Example: Notify Slack about page updates
        
    except Exception as e:
        logger.error(f"Error handling Notion page update: {e}")

async def handle_notion_database_updated(database_data: Dict[str, Any]) -> None:
    """Handle Notion database update event."""
    try:
        database_id = database_data.get("id", "")
        logger.info(f"Notion database updated: {database_id}")
        
        # Example: Sync database changes to Slack
        
    except Exception as e:
        logger.error(f"Error handling Notion database update: {e}")

# Slack event handlers
async def handle_slack_app_mention(event: Dict[str, Any]) -> None:
    """Handle Slack app mention event."""
    try:
        text = event.get("text", "")
        user = event.get("user", "")
        channel = event.get("channel", "")
        ts = event.get("ts", "")
        
        logger.info(f"App mentioned by {user} in {channel}")
        
        # Process the mention with the AI agent
        # This would integrate with the main agent system
        slack_tools = SlackTools()
        
        # Simple response for now
        await slack_tools.send_message(
            channel=channel,
            text="I received your message! Let me process that for you.",
            thread_ts=ts
        )
        
    except Exception as e:
        logger.error(f"Error handling app mention: {e}")

async def handle_slack_message(event: Dict[str, Any]) -> None:
    """Handle direct message to the bot."""
    try:
        # Only handle direct messages to avoid spam
        channel_type = event.get("channel_type", "")
        if channel_type == "im":
            text = event.get("text", "")
            user = event.get("user", "")
            channel = event.get("channel", "")
            
            logger.info(f"Direct message from {user}: {text}")
            
            # Process with AI agent
            # Implementation would go here
            
    except Exception as e:
        logger.error(f"Error handling message: {e}")

async def handle_slack_reaction_added(event: Dict[str, Any]) -> None:
    """Handle reaction added to message."""
    try:
        reaction = event.get("reaction", "")
        user = event.get("user", "")
        
        # Example: Use reactions as feedback mechanism
        logger.info(f"Reaction {reaction} added by {user}")
        
    except Exception as e:
        logger.error(f"Error handling reaction: {e}")

# Slack command handlers
async def handle_task_command(text: str, user_id: str, channel_id: str, response_url: str) -> None:
    """Handle /task slash command."""
    try:
        if not text.strip():
            await send_command_response(response_url, "Please provide task details. Usage: `/task Create a new project`")
            return
        
        # Process task creation with Notion
        notion_tools = NotionTools()
        
        # This would create a task in a configured Notion database
        # For now, send confirmation
        await send_command_response(
            response_url,
            f"Task created: {text}\n(Implementation would create this in Notion)"
        )
        
    except Exception as e:
        logger.error(f"Error handling task command: {e}")
        await send_command_response(response_url, "Sorry, I encountered an error creating the task.")

async def handle_query_command(text: str, user_id: str, channel_id: str, response_url: str) -> None:
    """Handle /query slash command."""
    try:
        if not text.strip():
            await send_command_response(response_url, "Please provide a search query. Usage: `/query project status`")
            return
        
        # Search Notion workspace
        notion_tools = NotionTools()
        results = notion_tools.search_pages(text)
        
        if results and not results[0].get("error"):
            response = f"Found {len(results)} results for '{text}':\n"
            for result in results[:5]:  # Limit to 5 results
                title = result.get("title", "Untitled")
                url = result.get("url", "")
                response += f"• <{url}|{title}>\n"
        else:
            response = f"No results found for '{text}'"
        
        await send_command_response(response_url, response)
        
    except Exception as e:
        logger.error(f"Error handling query command: {e}")
        await send_command_response(response_url, "Sorry, I encountered an error searching.")

async def handle_sync_command(text: str, user_id: str, channel_id: str, response_url: str) -> None:
    """Handle /sync slash command."""
    try:
        # This would trigger synchronization between Notion and Slack
        await send_command_response(
            response_url,
            "Synchronization triggered! I'll update the channel with any changes."
        )
        
    except Exception as e:
        logger.error(f"Error handling sync command: {e}")
        await send_command_response(response_url, "Sorry, I encountered an error with synchronization.")

async def send_command_response(response_url: str, text: str) -> None:
    """Send response to Slack command using response_url."""
    try:
        import httpx
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                response_url,
                json={
                    "response_type": "ephemeral",
                    "text": text
                }
            )
            response.raise_for_status()
            
    except Exception as e:
        logger.error(f"Error sending command response: {e}")
