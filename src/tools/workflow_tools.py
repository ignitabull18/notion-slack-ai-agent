"""
Workflow automation tools for complex Notion-Slack integrations.
"""
import asyncio
from typing import Dict, Any, List, Optional, Callable
from agno.tools import Tool
from datetime import datetime, timedelta
import json
import logging

from src.tools.notion_tools import NotionTools
from src.tools.slack_tools import SlackTools
from src.services.monitoring import track_notion_api_call, track_slack_api_call, PerformanceMonitor

logger = logging.getLogger(__name__)

class WorkflowTools(Tool):
    """Advanced workflow automation tools."""

    def __init__(self):
        super().__init__()
        self.notion_tools = NotionTools()
        self.slack_tools = SlackTools()

    async def sync_notion_to_slack(self, 
                                  database_id: str, 
                                  channel_id: str,
                                  filter_conditions: Optional[Dict] = None,
                                  template: Optional[str] = None) -> Dict[str, Any]:
        """Sync Notion database entries to Slack channel."""
        try:
            with PerformanceMonitor("notion_to_slack_sync"):
                # Query Notion database
                entries = self.notion_tools.query_database(
                    database_id=database_id,
                    filter_conditions=filter_conditions
                )
                
                if not entries or entries[0].get("error"):
                    return {
                        "success": False,
                        "error": "Failed to query Notion database",
                        "entries_processed": 0
                    }
                
                # Process each entry
                processed_count = 0
                errors = []
                
                for entry in entries:
                    try:
                        # Format entry for Slack
                        slack_message = self._format_notion_entry_for_slack(entry, template)
                        
                        # Send to Slack
                        result = await self.slack_tools.send_message(
                            channel=channel_id,
                            text=slack_message["text"],
                            blocks=slack_message.get("blocks")
                        )
                        
                        if result.get("success"):
                            processed_count += 1
                        else:
                            errors.append(f"Failed to send entry {entry.get('id', 'unknown')}")
                            
                    except Exception as e:
                        errors.append(f"Error processing entry {entry.get('id', 'unknown')}: {e}")
                
                return {
                    "success": True,
                    "entries_processed": processed_count,
                    "total_entries": len(entries),
                    "errors": errors
                }
                
        except Exception as e:
            logger.error(f"Error in notion to slack sync: {e}")
            return {
                "success": False,
                "error": str(e),
                "entries_processed": 0
            }

    async def create_task_from_slack_message(self,
                                           message: str,
                                           user_id: str,
                                           channel_id: str,
                                           database_id: str,
                                           default_properties: Optional[Dict] = None) -> Dict[str, Any]:
        """Create a Notion task from a Slack message."""
        try:
            with PerformanceMonitor("task_from_slack_message"):
                # Parse task details from message
                task_details = self._parse_task_from_message(message)
                
                # Get user info for assignment
                user_info = await self.slack_tools.get_user_info(user_id)
                
                # Prepare Notion properties
                properties = default_properties or {}
                properties.update({
                    "Status": {
                        "select": {"name": "Not Started"}
                    },
                    "Assignee": {
                        "rich_text": [{"text": {"content": user_info.get("user", {}).get("real_name", "Unknown")}}]
                    },
                    "Created From": {
                        "rich_text": [{"text": {"content": f"Slack message in <#{channel_id}>"}}]
                    },
                    "Due Date": {
                        "date": {"start": task_details.get("due_date")} if task_details.get("due_date") else None
                    }
                })
                
                # Remove None values
                properties = {k: v for k, v in properties.items() if v is not None}
                
                # Create page in Notion
                result = self.notion_tools.create_page(
                    parent_database_id=database_id,
                    title=task_details["title"],
                    properties=properties
                )
                
                if result.get("success"):
                    # Send confirmation to Slack
                    await self.slack_tools.send_message(
                        channel=channel_id,
                        text=f"✅ Task created: {task_details['title']}\n📄 <{result['url']}|View in Notion>"
                    )
                
                return result
                
        except Exception as e:
            logger.error(f"Error creating task from Slack message: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def daily_digest(self,
                          database_id: str,
                          channel_id: str,
                          lookback_hours: int = 24) -> Dict[str, Any]:
        """Generate and send a daily digest of Notion updates to Slack."""
        try:
            with PerformanceMonitor("daily_digest"):
                # Calculate time filter
                cutoff_time = datetime.now() - timedelta(hours=lookback_hours)
                
                # Query recent updates
                filter_conditions = {
                    "property": "Last edited time",
                    "date": {
                        "after": cutoff_time.isoformat()
                    }
                }
                
                entries = self.notion_tools.query_database(
                    database_id=database_id,
                    filter_conditions=filter_conditions,
                    sorts=[
                        {
                            "property": "Last edited time",
                            "direction": "descending"
                        }
                    ]
                )
                
                if not entries or entries[0].get("error"):
                    digest_text = f"📊 Daily Digest\nNo updates in the last {lookback_hours} hours."
                else:
                    digest_text = self._format_daily_digest(entries, lookback_hours)
                
                # Send digest to Slack
                result = await self.slack_tools.send_message(
                    channel=channel_id,
                    text=digest_text
                )
                
                return {
                    "success": result.get("success", False),
                    "entries_included": len(entries) if entries else 0,
                    "message_ts": result.get("ts")
                }
                
        except Exception as e:
            logger.error(f"Error generating daily digest: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def status_update_workflow(self,
                                   page_id: str,
                                   new_status: str,
                                   channel_id: str,
                                   notify_assignee: bool = True) -> Dict[str, Any]:
        """Update status in Notion and notify team in Slack."""
        try:
            with PerformanceMonitor("status_update_workflow"):
                # Get current page info
                page_info = self.notion_tools.get_page(page_id)
                if not page_info.get("success"):
                    return {
                        "success": False,
                        "error": "Failed to get page info"
                    }
                
                # Update status in Notion
                update_result = self.notion_tools.update_page(
                    page_id=page_id,
                    properties={
                        "Status": {
                            "select": {"name": new_status}
                        }
                    }
                )
                
                if not update_result.get("success"):
                    return update_result
                
                # Extract page details
                page = page_info["page"]
                title = self._extract_page_title(page)
                
                # Send notification to Slack
                status_emoji = self._get_status_emoji(new_status)
                notification_text = f"{status_emoji} *{title}*\nStatus updated to: *{new_status}*\n📄 <{page.get('url', '')}|View in Notion>"
                
                slack_result = await self.slack_tools.send_message(
                    channel=channel_id,
                    text=notification_text
                )
                
                return {
                    "success": True,
                    "notion_updated": True,
                    "slack_notified": slack_result.get("success", False),
                    "message_ts": slack_result.get("ts")
                }
                
        except Exception as e:
            logger.error(f"Error in status update workflow: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def smart_channel_routing(self,
                                   message: str,
                                   source_channel: str,
                                   routing_rules: List[Dict]) -> Dict[str, Any]:
        """Route messages to appropriate channels based on content analysis."""
        try:
            with PerformanceMonitor("smart_channel_routing"):
                routed_channels = []
                
                for rule in routing_rules:
                    if self._message_matches_rule(message, rule):
                        target_channel = rule["target_channel"]
                        custom_message = rule.get("template", message)
                        
                        # Send to target channel
                        result = await self.slack_tools.send_message(
                            channel=target_channel,
                            text=f"🔄 Routed from <#{source_channel}>:\n{custom_message}"
                        )
                        
                        if result.get("success"):
                            routed_channels.append(target_channel)
                
                return {
                    "success": True,
                    "routed_to": routed_channels,
                    "total_routes": len(routed_channels)
                }
                
        except Exception as e:
            logger.error(f"Error in smart channel routing: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    # Helper methods
    def _format_notion_entry_for_slack(self, entry: Dict, template: Optional[str] = None) -> Dict[str, Any]:
        """Format a Notion entry for Slack display."""
        if template:
            # Use custom template
            formatted_text = template.format(**entry)
        else:
            # Default formatting
            title = self._extract_page_title(entry)
            url = entry.get("url", "")
            last_edited = entry.get("last_edited_time", "")
            
            formatted_text = f"📄 *{title}*\n🔗 <{url}|View in Notion>\n📅 Last edited: {last_edited}"
        
        return {
            "text": formatted_text,
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": formatted_text
                    }
                }
            ]
        }

    def _parse_task_from_message(self, message: str) -> Dict[str, Any]:
        """Parse task details from a message."""
        # Simple parsing logic - could be enhanced with NLP
        lines = message.split('\n')
        title = lines[0] if lines else message
        
        # Look for due date patterns
        due_date = None
        for line in lines:
            if "due:" in line.lower() or "deadline:" in line.lower():
                # Extract date - this would need more sophisticated parsing
                pass
        
        return {
            "title": title.strip(),
            "description": message,
            "due_date": due_date
        }

    def _format_daily_digest(self, entries: List[Dict], hours: int) -> str:
        """Format entries into a daily digest."""
        digest_parts = [f"📊 *Daily Digest* - Last {hours} hours\n"]
        
        for i, entry in enumerate(entries[:10]):  # Limit to 10 entries
            title = self._extract_page_title(entry)
            url = entry.get("url", "")
            digest_parts.append(f"{i+1}. <{url}|{title}>")
        
        if len(entries) > 10:
            digest_parts.append(f"... and {len(entries) - 10} more updates")
        
        return "\n".join(digest_parts)

    def _extract_page_title(self, page: Dict) -> str:
        """Extract title from a Notion page."""
        try:
            properties = page.get("properties", {})
            if "Name" in properties:
                title_prop = properties["Name"]
                if "title" in title_prop and title_prop["title"]:
                    return title_prop["title"][0]["text"]["content"]
            elif "Title" in properties:
                title_prop = properties["Title"]
                if "title" in title_prop and title_prop["title"]:
                    return title_prop["title"][0]["text"]["content"]
            return "Untitled"
        except (KeyError, IndexError, TypeError):
            return "Untitled"

    def _get_status_emoji(self, status: str) -> str:
        """Get emoji for status."""
        status_emojis = {
            "not started": "⚪",
            "in progress": "🟡",
            "completed": "✅",
            "blocked": "🔴",
            "on hold": "⏸️"
        }
        return status_emojis.get(status.lower(), "📝")

    def _message_matches_rule(self, message: str, rule: Dict) -> bool:
        """Check if message matches routing rule."""
        keywords = rule.get("keywords", [])
        pattern = rule.get("pattern", "")
        
        message_lower = message.lower()
        
        # Check keywords
        if keywords:
            for keyword in keywords:
                if keyword.lower() in message_lower:
                    return True
        
        # Check regex pattern (if provided)
        if pattern:
            import re
            return bool(re.search(pattern, message, re.IGNORECASE))
        
        return False

class AutomationScheduler:
    """Schedule and manage automated workflows."""
    
    def __init__(self):
        self.scheduled_tasks = {}
        self.workflow_tools = WorkflowTools()
    
    async def schedule_daily_digest(self, 
                                   database_id: str, 
                                   channel_id: str, 
                                   time_str: str = "09:00") -> str:
        """Schedule a daily digest workflow."""
        task_id = f"digest_{database_id}_{channel_id}"
        
        # This would integrate with a task scheduler like Celery
        # For now, just store the configuration
        self.scheduled_tasks[task_id] = {
            "type": "daily_digest",
            "database_id": database_id,
            "channel_id": channel_id,
            "time": time_str,
            "active": True
        }
        
        logger.info(f"Scheduled daily digest: {task_id}")
        return task_id
    
    async def schedule_status_reminders(self, 
                                       database_id: str, 
                                       channel_id: str, 
                                       reminder_days: int = 3) -> str:
        """Schedule reminders for stale tasks."""
        task_id = f"reminders_{database_id}_{channel_id}"
        
        self.scheduled_tasks[task_id] = {
            "type": "status_reminders",
            "database_id": database_id,
            "channel_id": channel_id,
            "reminder_days": reminder_days,
            "active": True
        }
        
        logger.info(f"Scheduled status reminders: {task_id}")
        return task_id
    
    def get_scheduled_tasks(self) -> Dict[str, Dict]:
        """Get all scheduled tasks."""
        return self.scheduled_tasks.copy()
    
    def cancel_task(self, task_id: str) -> bool:
        """Cancel a scheduled task."""
        if task_id in self.scheduled_tasks:
            self.scheduled_tasks[task_id]["active"] = False
            logger.info(f"Cancelled task: {task_id}")
            return True
        return False
