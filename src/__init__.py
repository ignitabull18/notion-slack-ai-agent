"""
Notion-Slack AI Agent

AI-powered integration between Notion and Slack using Agno framework
for intelligent task management, knowledge synchronization, and workflow automation.
"""

__version__ = "1.0.0"
__author__ = "Your Name"
__email__ = "your.email@example.com"

# Package exports
from src.agents.notion_slack_agent import NotionSlackAgent
from src.config import Settings, get_settings

__all__ = [
    "NotionSlackAgent",
    "Settings",
    "get_settings",
]