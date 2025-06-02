"""
Slack-specific tools for the AI agent.
"""
import asyncio
from typing import List, Dict, Any, Optional
from agno.tools import Tool
from slack_sdk.web.async_client import AsyncWebClient
from slack_sdk.errors import SlackApiError
from src.config import get_settings

class SlackTools(Tool):
    """Tools for interacting with Slack API."""

    def __init__(self):
        super().__init__()
        settings = get_settings()
        self.client = AsyncWebClient(token=settings.slack_bot_token)

    async def send_message(self, 
                          channel: str,
                          text: str,
                          blocks: Optional[List[Dict]] = None,
                          thread_ts: Optional[str] = None,
                          attachments: Optional[List[Dict]] = None) -> Dict[str, Any]:
        """Send a message to a Slack channel or user."""
        try:
            response = await self.client.chat_postMessage(
                channel=channel,
                text=text,
                blocks=blocks,
                thread_ts=thread_ts,
                attachments=attachments
            )
            return {
                "success": True,
                "ts": response["ts"],
                "channel": response["channel"],
                "message": "Message sent successfully"
            }
        except SlackApiError as e:
            return {
                "success": False,
                "error": e.response["error"],
                "message": f"Failed to send message: {e.response['error']}"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to send message"
            }

    async def update_message(self,
                            channel: str,
                            ts: str,
                            text: str,
                            blocks: Optional[List[Dict]] = None) -> Dict[str, Any]:
        """Update an existing Slack message."""
        try:
            response = await self.client.chat_update(
                channel=channel,
                ts=ts,
                text=text,
                blocks=blocks
            )
            return {
                "success": True,
                "ts": response["ts"],
                "channel": response["channel"],
                "message": "Message updated successfully"
            }
        except SlackApiError as e:
            return {
                "success": False,
                "error": e.response["error"],
                "message": f"Failed to update message: {e.response['error']}"
            }

    async def get_channel_info(self, channel_id: str) -> Dict[str, Any]:
        """Get information about a Slack channel."""
        try:
            response = await self.client.conversations_info(channel=channel_id)
            channel = response["channel"]
            return {
                "success": True,
                "channel": {
                    "id": channel["id"],
                    "name": channel["name"],
                    "is_private": channel["is_private"],
                    "is_archived": channel.get("is_archived", False),
                    "member_count": channel.get("num_members", 0),
                    "topic": channel.get("topic", {}).get("value", ""),
                    "purpose": channel.get("purpose", {}).get("value", ""),
                    "created": channel.get("created", 0)
                }
            }
        except SlackApiError as e:
            return {
                "success": False,
                "error": e.response["error"],
                "message": f"Failed to get channel info: {e.response['error']}"
            }

    async def list_channels(self, 
                           types: str = "public_channel,private_channel",
                           exclude_archived: bool = True,
                           limit: int = 1000) -> List[Dict]:
        """List accessible Slack channels."""
        try:
            response = await self.client.conversations_list(
                types=types,
                exclude_archived=exclude_archived,
                limit=limit
            )
            return [{
                "id": channel["id"],
                "name": channel["name"],
                "is_private": channel["is_private"],
                "is_archived": channel.get("is_archived", False),
                "member_count": channel.get("num_members", 0),
                "topic": channel.get("topic", {}).get("value", ""),
                "purpose": channel.get("purpose", {}).get("value", "")
            } for channel in response["channels"]]
        except SlackApiError as e:
            return [{"error": e.response["error"]}]

    async def get_user_info(self, user_id: str) -> Dict[str, Any]:
        """Get information about a Slack user."""
        try:
            response = await self.client.users_info(user=user_id)
            user = response["user"]
            return {
                "success": True,
                "user": {
                    "id": user["id"],
                    "name": user["name"],
                    "real_name": user.get("real_name", ""),
                    "display_name": user.get("profile", {}).get("display_name", ""),
                    "email": user.get("profile", {}).get("email", ""),
                    "is_bot": user.get("is_bot", False),
                    "is_admin": user.get("is_admin", False),
                    "timezone": user.get("tz", ""),
                    "status_text": user.get("profile", {}).get("status_text", ""),
                    "status_emoji": user.get("profile", {}).get("status_emoji", "")
                }
            }
        except SlackApiError as e:
            return {
                "success": False,
                "error": e.response["error"],
                "message": f"Failed to get user info: {e.response['error']}"
            }

    async def add_reaction(self, 
                          channel: str, 
                          timestamp: str, 
                          name: str) -> Dict[str, Any]:
        """Add a reaction to a message."""
        try:
            await self.client.reactions_add(
                channel=channel,
                timestamp=timestamp,
                name=name
            )
            return {
                "success": True,
                "message": f"Added reaction: {name}"
            }
        except SlackApiError as e:
            return {
                "success": False,
                "error": e.response["error"],
                "message": f"Failed to add reaction: {e.response['error']}"
            }

    async def get_channel_members(self, channel_id: str) -> List[Dict]:
        """Get members of a Slack channel."""
        try:
            response = await self.client.conversations_members(channel=channel_id)
            member_ids = response["members"]
            
            # Get user info for each member
            members = []
            for user_id in member_ids:
                user_info = await self.get_user_info(user_id)
                if user_info.get("success"):
                    members.append(user_info["user"])
            
            return members
        except SlackApiError as e:
            return [{"error": e.response["error"]}]

    async def create_channel(self, 
                            name: str, 
                            is_private: bool = False) -> Dict[str, Any]:
        """Create a new Slack channel."""
        try:
            response = await self.client.conversations_create(
                name=name,
                is_private=is_private
            )
            channel = response["channel"]
            return {
                "success": True,
                "channel": {
                    "id": channel["id"],
                    "name": channel["name"],
                    "is_private": channel["is_private"]
                },
                "message": f"Created channel: #{name}"
            }
        except SlackApiError as e:
            return {
                "success": False,
                "error": e.response["error"],
                "message": f"Failed to create channel: {e.response['error']}"
            }

    async def set_channel_topic(self, 
                               channel: str, 
                               topic: str) -> Dict[str, Any]:
        """Set the topic for a Slack channel."""
        try:
            response = await self.client.conversations_setTopic(
                channel=channel,
                topic=topic
            )
            return {
                "success": True,
                "topic": response["topic"]["value"],
                "message": "Channel topic updated successfully"
            }
        except SlackApiError as e:
            return {
                "success": False,
                "error": e.response["error"],
                "message": f"Failed to set channel topic: {e.response['error']}"
            }

    async def invite_to_channel(self, 
                               channel: str, 
                               users: List[str]) -> Dict[str, Any]:
        """Invite users to a Slack channel."""
        try:
            response = await self.client.conversations_invite(
                channel=channel,
                users=",".join(users)
            )
            return {
                "success": True,
                "channel": response["channel"]["id"],
                "message": f"Invited {len(users)} users to channel"
            }
        except SlackApiError as e:
            return {
                "success": False,
                "error": e.response["error"],
                "message": f"Failed to invite users: {e.response['error']}"
            }

    async def get_message_history(self, 
                                 channel: str, 
                                 limit: int = 100,
                                 oldest: Optional[str] = None,
                                 latest: Optional[str] = None) -> List[Dict]:
        """Get message history from a Slack channel."""
        try:
            params = {"channel": channel, "limit": limit}
            if oldest:
                params["oldest"] = oldest
            if latest:
                params["latest"] = latest
                
            response = await self.client.conversations_history(**params)
            return [{
                "ts": message["ts"],
                "user": message.get("user", ""),
                "text": message.get("text", ""),
                "type": message.get("type", ""),
                "subtype": message.get("subtype", ""),
                "thread_ts": message.get("thread_ts", "")
            } for message in response["messages"]]
        except SlackApiError as e:
            return [{"error": e.response["error"]}]
