"""
Main Notion-Slack AI Agent implementation.
"""
import logging
import json
from typing import Any, Dict, List, Optional
from datetime import datetime

from agno.models.openai import OpenAI
from agno.models.anthropic import Anthropic
from agno.storage.agent import AgentStorage
from agno.tools import ReasoningTools, MemoryTools

from src.agents.base_agent import BaseAgent
from src.tools.notion_tools import NotionTools
from src.tools.slack_tools import SlackTools
from src.tools.workflow_tools import WorkflowTools
from src.tools.search_tools import SearchTools
from src.config import get_settings
from src.services.rate_limiter import RateLimiter
from src.utils.errors import InvalidRequestError, SecurityError

logger = logging.getLogger(__name__)

class NotionSlackAgent(BaseAgent):
    """Main orchestrator agent for Notion-Slack integration."""
    
    def __init__(self):
        """Initialize the Notion-Slack agent."""
        settings = get_settings()
        
        # Select model based on provider
        if settings.model_provider == "openai":
            model = OpenAI(id=settings.model_id, api_key=settings.openai_api_key)
        elif settings.model_provider == "anthropic":
            model = Anthropic(id=settings.model_id, api_key=settings.anthropic_api_key)
        else:
            raise ValueError(f"Unsupported model provider: {settings.model_provider}")
        
        # Initialize tools
        tools = [
            NotionTools(),
            SlackTools(),
            WorkflowTools(),
            SearchTools(),
            ReasoningTools(),
            MemoryTools()
        ]
        
        # Agent instructions
        instructions = [
            "You are the central coordinator for Notion-Slack integration.",
            "Your capabilities include:",
            "- Process Slack messages containing Notion operations",
            "- Maintain context across threaded conversations",
            "- Route tasks to specialized tools when needed",
            "- Execute complex workflows across both platforms",
            "- Provide intelligent responses based on context",
            "Security protocols:",
            "- Always validate inputs before processing",
            "- Never expose sensitive information",
            "- Log all operations for audit trail",
            "- Enforce user permissions and access controls",
            "Response guidelines:",
            "- Be concise but informative",
            "- Use formatting for better readability",
            "- Provide actionable suggestions",
            "- Handle errors gracefully with helpful messages"
        ]
        
        # Initialize storage
        storage = AgentStorage(
            table_name="notion_slack_sessions",
            db_file="agent_storage.db"
        )
        
        super().__init__(
            name="NotionSlackOrchestrator",
            model=model,
            tools=tools,
            storage=storage,
            description="AI agent for seamless Notion-Slack integration",
            instructions=instructions,
            show_tool_calls=True,
            markdown=True
        )
        
        # Initialize rate limiter
        self.rate_limiter = RateLimiter()
        
        # Security settings
        self.allowed_operations = {
            "database.create",
            "database.query",
            "page.create",
            "page.update",
            "page.get",
            "block.append",
            "search.query",
            "slack.send_message",
            "slack.get_channel_info",
            "slack.list_channels"
        }
    
    async def validate_request(self, request: str) -> bool:
        """Validate if the request can be processed."""
        # Basic validation
        if not request or len(request.strip()) == 0:
            return False
        
        # Length validation
        if len(request) > 10000:
            logger.warning(f"Request too long: {len(request)} characters")
            return False
        
        # Check for potential security issues
        dangerous_patterns = [
            "<script",
            "javascript:",
            "eval(",
            "exec(",
            "__import__"
        ]
        
        request_lower = request.lower()
        for pattern in dangerous_patterns:
            if pattern in request_lower:
                logger.warning(f"Potentially dangerous pattern detected: {pattern}")
                return False
        
        return True
    
    async def process_request(
        self,
        request: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Process a request and return a response."""
        try:
            # Validate request
            if not await self.validate_request(request):
                raise InvalidRequestError("Invalid request format or content")
            
            # Check rate limit
            user_id = context.get("user_id", "anonymous") if context else "anonymous"
            if not await self.rate_limiter.check_limit(user_id):
                return {
                    "success": False,
                    "error": "Rate limit exceeded. Please try again later.",
                    "retry_after": await self.rate_limiter.get_retry_after(user_id)
                }
            
            # Prepare context
            enhanced_context = self._prepare_context(context)
            
            # Log request
            logger.info(f"Processing request from user {user_id}: {request[:100]}...")
            
            # Process with agent
            session_id = enhanced_context.get("session_id", f"session_{user_id}")
            response = await self.agent.run(
                request,
                session_id=session_id,
                context=enhanced_context
            )
            
            # Format response
            formatted_response = self._format_response(response)
            
            # Log success
            logger.info(f"Successfully processed request for user {user_id}")
            
            return {
                "success": True,
                "response": formatted_response,
                "session_id": session_id,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except InvalidRequestError as e:
            logger.error(f"Invalid request: {e}")
            return {
                "success": False,
                "error": str(e),
                "type": "invalid_request"
            }
        except SecurityError as e:
            logger.error(f"Security error: {e}")
            return {
                "success": False,
                "error": "Security validation failed",
                "type": "security_error"
            }
        except Exception as e:
            logger.error(f"Error processing request: {e}", exc_info=True)
            return {
                "success": False,
                "error": "An unexpected error occurred. Please try again.",
                "type": "internal_error"
            }
    
    def _prepare_context(self, context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Prepare and enhance context for the agent."""
        enhanced_context = context.copy() if context else {}
        
        # Add timestamp
        enhanced_context["timestamp"] = datetime.utcnow().isoformat()
        
        # Add allowed operations
        enhanced_context["allowed_operations"] = list(self.allowed_operations)
        
        # Add environment info
        settings = get_settings()
        enhanced_context["environment"] = settings.environment
        
        return enhanced_context
    
    def _format_response(self, response: Any) -> str:
        """Format the agent response for output."""
        if isinstance(response, dict):
            return json.dumps(response, indent=2)
        elif isinstance(response, (list, tuple)):
            return json.dumps(response, indent=2)
        else:
            return str(response)
    
    async def process_slack_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Process a Slack event."""
        event_type = event.get("type")
        
        if event_type == "app_mention":
            return await self._handle_app_mention(event)
        elif event_type == "message":
            return await self._handle_message(event)
        elif event_type == "slash_command":
            return await self._handle_slash_command(event)
        else:
            logger.warning(f"Unhandled event type: {event_type}")
            return {
                "success": False,
                "error": f"Unhandled event type: {event_type}"
            }
    
    async def _handle_app_mention(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Handle app mention events."""
        text = event.get("text", "")
        user = event.get("user")
        channel = event.get("channel")
        
        # Remove bot mention from text
        cleaned_text = text.split(">", 1)[-1].strip() if ">" in text else text
        
        context = {
            "user_id": user,
            "channel_id": channel,
            "event_type": "app_mention",
            "thread_ts": event.get("thread_ts")
        }
        
        return await self.process_request(cleaned_text, context)
    
    async def _handle_message(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Handle direct message events."""
        text = event.get("text", "")
        user = event.get("user")
        channel = event.get("channel")
        
        context = {
            "user_id": user,
            "channel_id": channel,
            "event_type": "message",
            "thread_ts": event.get("thread_ts")
        }
        
        return await self.process_request(text, context)
    
    async def _handle_slash_command(self, command: Dict[str, Any]) -> Dict[str, Any]:
        """Handle slash command events."""
        command_name = command.get("command")
        text = command.get("text", "")
        user_id = command.get("user_id")
        channel_id = command.get("channel_id")
        
        # Build request based on command
        if command_name == "/task":
            request = f"Create a task: {text}"
        elif command_name == "/query":
            request = f"Query Notion: {text}"
        elif command_name == "/sync":
            request = f"Sync data: {text}"
        else:
            request = text
        
        context = {
            "user_id": user_id,
            "channel_id": channel_id,
            "event_type": "slash_command",
            "command": command_name
        }
        
        return await self.process_request(request, context)