"""
Tests for Notion and Slack tools.
"""
import pytest
from unittest.mock import Mock, patch
from src.tools.notion_tools import NotionTools
from src.tools.slack_tools import SlackTools

class TestNotionTools:
    """Test cases for Notion tools."""
    
    def test_create_page_success(self, mock_notion_client, test_settings):
        """Test successful page creation."""
        # Arrange
        tools = NotionTools()
        database_id = "test_database_id"
        title = "Test Page"
        properties = {"Status": {"select": {"name": "In Progress"}}}
        
        # Act
        result = tools.create_page(database_id, title, properties)
        
        # Assert
        assert result["success"] is True
        assert result["page_id"] == "test_page_id"
        assert result["url"] == "https://notion.so/test_page"
        mock_notion_client.pages.create.assert_called_once()
    
    def test_create_page_failure(self, mock_notion_client, test_settings):
        """Test page creation failure."""
        # Arrange
        tools = NotionTools()
        mock_notion_client.pages.create.side_effect = Exception("API Error")
        
        # Act
        result = tools.create_page("test_db", "Test", {})
        
        # Assert
        assert result["success"] is False
        assert "error" in result
    
    def test_query_database_success(self, mock_notion_client, test_settings):
        """Test successful database query."""
        # Arrange
        tools = NotionTools()
        database_id = "test_database_id"
        
        # Act
        result = tools.query_database(database_id)
        
        # Assert
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["id"] == "test_page_id"
        mock_notion_client.databases.query.assert_called_once()
    
    def test_query_database_with_filters(self, mock_notion_client, test_settings):
        """Test database query with filters."""
        # Arrange
        tools = NotionTools()
        database_id = "test_database_id"
        filters = {"property": "Status", "select": {"equals": "Done"}}
        
        # Act
        result = tools.query_database(database_id, filters)
        
        # Assert
        mock_notion_client.databases.query.assert_called_with(
            database_id=database_id,
            filter=filters
        )
    
    def test_update_page_success(self, mock_notion_client, test_settings):
        """Test successful page update."""
        # Arrange
        tools = NotionTools()
        mock_notion_client.pages.update.return_value = {"id": "test_page_id"}
        
        # Act
        result = tools.update_page("test_page_id", {"Status": {"select": {"name": "Done"}}})
        
        # Assert
        assert result["success"] is True
        mock_notion_client.pages.update.assert_called_once()
    
    def test_search_pages(self, mock_notion_client, test_settings):
        """Test page search functionality."""
        # Arrange
        tools = NotionTools()
        mock_notion_client.search.return_value = {
            "results": [
                {
                    "id": "page1",
                    "object": "page",
                    "url": "https://notion.so/page1",
                    "properties": {"Name": {"title": [{"text": {"content": "Search Result"}}]}}
                }
            ]
        }
        
        # Act
        result = tools.search_pages("test query")
        
        # Assert
        assert len(result) == 1
        assert result[0]["id"] == "page1"
        mock_notion_client.search.assert_called_once()

class TestSlackTools:
    """Test cases for Slack tools."""
    
    @pytest.mark.asyncio
    async def test_send_message_success(self, mock_slack_client, test_settings):
        """Test successful message sending."""
        # Arrange
        tools = SlackTools()
        
        # Act
        result = await tools.send_message(
            channel="C1234567890",
            text="Test message"
        )
        
        # Assert
        assert result["success"] is True
        assert result["ts"] == "1234567890.123456"
        mock_slack_client.chat_postMessage.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_send_message_with_blocks(self, mock_slack_client, test_settings):
        """Test sending message with blocks."""
        # Arrange
        tools = SlackTools()
        blocks = [{"type": "section", "text": {"type": "mrkdwn", "text": "Hello"}}]
        
        # Act
        result = await tools.send_message(
            channel="C1234567890",
            text="Test message",
            blocks=blocks
        )
        
        # Assert
        mock_slack_client.chat_postMessage.assert_called_with(
            channel="C1234567890",
            text="Test message",
            blocks=blocks,
            thread_ts=None,
            attachments=None
        )
    
    @pytest.mark.asyncio
    async def test_get_channel_info_success(self, mock_slack_client, test_settings):
        """Test getting channel information."""
        # Arrange
        tools = SlackTools()
        
        # Act
        result = await tools.get_channel_info("C1234567890")
        
        # Assert
        assert result["success"] is True
        assert result["channel"]["id"] == "C1234567890"
        assert result["channel"]["name"] == "test-channel"
        mock_slack_client.conversations_info.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_list_channels(self, mock_slack_client, test_settings):
        """Test listing channels."""
        # Arrange
        tools = SlackTools()
        mock_slack_client.conversations_list.return_value = {
            "channels": [
                {
                    "id": "C1234567890",
                    "name": "general",
                    "is_private": False,
                    "num_members": 10
                }
            ]
        }
        
        # Act
        result = await tools.list_channels()
        
        # Assert
        assert len(result) == 1
        assert result[0]["id"] == "C1234567890"
        mock_slack_client.conversations_list.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_add_reaction_success(self, mock_slack_client, test_settings):
        """Test adding reaction to message."""
        # Arrange
        tools = SlackTools()
        
        # Act
        result = await tools.add_reaction("C1234567890", "1234567890.123456", "thumbsup")
        
        # Assert
        assert result["success"] is True
        mock_slack_client.reactions_add.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_channel_success(self, mock_slack_client, test_settings):
        """Test creating a new channel."""
        # Arrange
        tools = SlackTools()
        mock_slack_client.conversations_create.return_value = {
            "channel": {
                "id": "C9876543210",
                "name": "new-channel",
                "is_private": False
            }
        }
        
        # Act
        result = await tools.create_channel("new-channel")
        
        # Assert
        assert result["success"] is True
        assert result["channel"]["id"] == "C9876543210"
        mock_slack_client.conversations_create.assert_called_once()

class TestToolIntegration:
    """Integration tests for tools working together."""
    
    @pytest.mark.asyncio
    async def test_notion_to_slack_workflow(self, mock_notion_client, mock_slack_client, test_settings):
        """Test workflow from Notion to Slack."""
        # Arrange
        notion_tools = NotionTools()
        slack_tools = SlackTools()
        
        # Create page in Notion
        page_result = notion_tools.create_page(
            "test_database_id",
            "New Task",
            {"Status": {"select": {"name": "To Do"}}}
        )
        
        # Send notification to Slack
        slack_result = await slack_tools.send_message(
            "C1234567890",
            f"New task created: {page_result['url']}"
        )
        
        # Assert both operations succeeded
        assert page_result["success"] is True
        assert slack_result["success"] is True
    
    def test_search_and_share_workflow(self, mock_notion_client, mock_slack_client, test_settings):
        """Test searching Notion and sharing results in Slack."""
        # Arrange
        notion_tools = NotionTools()
        
        # Mock search results
        mock_notion_client.search.return_value = {
            "results": [
                {
                    "id": "result1",
                    "object": "page",
                    "url": "https://notion.so/result1",
                    "properties": {"Name": {"title": [{"text": {"content": "Found Page"}}]}}
                }
            ]
        }
        
        # Act
        search_results = notion_tools.search_pages("important project")
        
        # Assert
        assert len(search_results) == 1
        assert search_results[0]["title"] == "Found Page"
        
        # This would continue with sending results to Slack
        # but we'll keep the test focused on the search functionality
