"""
Base agent class for the Notion-Slack AI Agent system.
"""
import logging
from typing import Any, Dict, List, Optional
from abc import ABC, abstractmethod
from agno.agent import Agent
from agno.models.base import BaseModel
from agno.storage.agent import AgentStorage

logger = logging.getLogger(__name__)

class BaseAgent(ABC):
    """Abstract base class for all agents in the system."""
    
    def __init__(
        self,
        name: str,
        model: BaseModel,
        tools: Optional[List[Any]] = None,
        storage: Optional[AgentStorage] = None,
        description: str = "",
        instructions: Optional[List[str]] = None,
        **kwargs
    ):
        """Initialize the base agent."""
        self.name = name
        self.description = description
        self.tools = tools or []
        self.instructions = instructions or []
        
        # Initialize Agno agent
        self.agent = Agent(
            name=name,
            model=model,
            tools=tools,
            storage=storage,
            description=description,
            instructions=instructions,
            **kwargs
        )
        
        logger.info(f"Initialized {self.name} agent")
    
    @abstractmethod
    async def process_request(self, request: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Process a request and return a response."""
        pass
    
    @abstractmethod
    async def validate_request(self, request: str) -> bool:
        """Validate if the request can be processed."""
        pass
    
    async def get_memory(self, session_id: str) -> List[Dict[str, Any]]:
        """Retrieve conversation memory for a session."""
        if self.agent.storage:
            return await self.agent.storage.get_messages(session_id)
        return []
    
    async def save_memory(self, session_id: str, message: Dict[str, Any]) -> None:
        """Save a message to conversation memory."""
        if self.agent.storage:
            await self.agent.storage.add_message(session_id, message)
    
    def add_tool(self, tool: Any) -> None:
        """Add a tool to the agent."""
        self.tools.append(tool)
        self.agent.tools.append(tool)
    
    def update_instructions(self, instructions: List[str]) -> None:
        """Update agent instructions."""
        self.instructions = instructions
        self.agent.instructions = instructions
    
    async def reset_session(self, session_id: str) -> None:
        """Reset a conversation session."""
        if self.agent.storage:
            await self.agent.storage.clear_messages(session_id)
    
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(name='{self.name}')>"