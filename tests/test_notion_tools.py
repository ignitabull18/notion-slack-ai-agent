"""
Tests for Notion tools functionality.
"""
import pytest
from unittest.mock import patch, Mock
from src.tools.notion_tools import NotionTools
from src.utils.errors import NotionError

class TestNotionTools:
    """Test suite for Notion tools."""
    
    @pytest.fixture
    def notion_tools(self, mock_notion_client):
        """Create NotionTools instance with mocked client."""
        tools = NotionTools()
        tools.client = mock_notion_client
        return tools
    
    def test_create_page_success(self, notion_tools, mock_notion_client):
        """Test successful page creation."""
        # Arrange
        database_id = "test-database-id"
        title = "Test Page"
        properties = {"Status": {"select": {"name": "In Progress"}}}
        
        # Act
        result = notion_tools.create_page(database_id, title, properties)
        
        # Assert
        assert result["success"] is True
        assert result["page_id"] == "test-page-id"
        assert result["url"] == "https://notion.so/test-page"
        assert "Created page: Test Page" in result["message"]
        
        # Verify API call
        mock_notion_client.pages.create.assert_called_once()
        call_args = mock_notion_client.pages.create.call_args[1]
        assert call_args["parent"]["database_id"] == database_id
        assert call_args["properties"]["Name"]["title"][0]["text"]["content"] == title
    
    def test_create_page_failure(self, notion_tools, mock_notion_client):
        """Test page creation failure."""
        # Arrange
        mock_notion_client.pages.create.side_effect = Exception("API Error")
        
        # Act
        result = notion_tools.create_page("db-id", "title", {})
        
        # Assert
        assert result["success"] is False
        assert "API Error" in result["error"]
        assert "Failed to create page" in result["message"]
    
    def test_query_database_success(self, notion_tools, mock_notion_client):
        """Test successful database query."""
        # Arrange
        database_id = "test-database-id"
        filter_conditions = {"property": "Status", "select": {"equals": "In Progress"}}
        
        # Act
        result = notion_tools.query_database(database_id, filter_conditions)
        
        # Assert
        assert len(result) == 1
        assert result[0]["id"] == "test-page-id"
        assert "properties" in result[0]
        assert "url" in result[0]
        
        # Verify API call
        mock_notion_client.databases.query.assert_called_once_with(
            database_id=database_id,
            filter=filter_conditions
        )
    
    def test_query_database_with_sorts(self, notion_tools, mock_notion_client):
        """Test database query with sorting."""
        # Arrange
        database_id = "test-database-id"
        sorts = [{"property": "Created", "direction": "descending"}]
        
        # Act
        result = notion_tools.query_database(database_id, sorts=sorts)
        
        # Assert
        assert len(result) == 1
        
        # Verify API call
        mock_notion_client.databases.query.assert_called_once_with(
            database_id=database_id,
            sorts=sorts
        )
    
    def test_query_database_failure(self, notion_tools, mock_notion_client):
        """Test database query failure."""
        # Arrange
        mock_notion_client.databases.query.side_effect = Exception("Query failed")
        
        # Act
        result = notion_tools.query_database("db-id")
        
        # Assert
        assert len(result) == 1
        assert "error" in result[0]
        assert "Query failed" in result[0]["error"]
    
    def test_update_page_success(self, notion_tools, mock_notion_client):
        """Test successful page update."""
        # Arrange
        page_id = "test-page-id"
        properties = {"Status": {"select": {"name": "Completed"}}}
        mock_notion_client.pages.update.return_value = {"id": page_id}
        
        # Act
        result = notion_tools.update_page(page_id, properties)
        
        # Assert
        assert result["success"] is True
        assert result["page_id"] == page_id
        assert "Page updated successfully" in result["message"]
        
        # Verify API call
        mock_notion_client.pages.update.assert_called_once_with(
            page_id=page_id,
            properties=properties
        )
    
    def test_get_page_success(self, notion_tools, mock_notion_client):
        """Test successful page retrieval."""
        # Arrange
        page_id = "test-page-id"
        
        # Act
        result = notion_tools.get_page(page_id)
        
        # Assert
        assert result["success"] is True
        assert result["page"]["id"] == page_id
        assert "properties" in result["page"]
        
        # Verify API call
        mock_notion_client.pages.retrieve.assert_called_once_with(page_id)
    
    def test_search_pages_success(self, notion_tools, mock_notion_client):
        """Test successful page search."""
        # Arrange
        query = "test search"
        
        # Act
        result = notion_tools.search_pages(query)
        
        # Assert
        assert len(result) == 1
        assert result[0]["id"] == "test-page-id"
        assert result[0]["object"] == "page"
        
        # Verify API call
        mock_notion_client.search.assert_called_once_with(query=query)
    
    def test_search_pages_with_filter(self, notion_tools, mock_notion_client):
        """Test page search with filter."""
        # Arrange
        query = "test search"
        filter_type = "page"
        
        # Act
        result = notion_tools.search_pages(query, filter_type)
        
        # Assert
        assert len(result) == 1
        
        # Verify API call
        expected_params = {
            "query": query,
            "filter": {"property": "object", "value": filter_type}
        }
        mock_notion_client.search.assert_called_once_with(**expected_params)
    
    def test_get_database_schema_success(self, notion_tools, mock_notion_client):
        """Test successful database schema retrieval."""
        # Arrange
        database_id = "test-database-id"
        mock_notion_client.databases.retrieve.return_value = {
            "id": database_id,
            "title": [{"text": {"content": "Test Database"}}],
            "properties": {"Name": {"title": {}}},
            "url": "https://notion.so/test-db"
        }
        
        # Act
        result = notion_tools.get_database_schema(database_id)
        
        # Assert
        assert result["success"] is True
        assert result["database"]["id"] == database_id
        assert "properties" in result["database"]
        
        # Verify API call
        mock_notion_client.databases.retrieve.assert_called_once_with(database_id)
    
    def test_append_block_children_success(self, notion_tools, mock_notion_client):
        """Test successful block children append."""
        # Arrange
        block_id = "test-block-id"
        children = [
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"type": "text", "text": {"content": "Test content"}}]
                }
            }
        ]
        mock_notion_client.blocks.children.append.return_value = {"results": children}
        
        # Act
        result = notion_tools.append_block_children(block_id, children)
        
        # Assert
        assert result["success"] is True
        assert result["results"] == children
        assert "Blocks appended successfully" in result["message"]
        
        # Verify API call
        mock_notion_client.blocks.children.append.assert_called_once_with(
            block_id=block_id,
            children=children
        )
    
    def test_extract_title_from_title_property(self, notion_tools):
        """Test title extraction from title property."""
        # Arrange
        notion_object = {
            "properties": {
                "Name": {
                    "title": [{"text": {"content": "Test Title"}}]
                }
            }
        }
        
        # Act
        title = notion_tools._extract_title(notion_object)
        
        # Assert
        assert title == "Test Title"
    
    def test_extract_title_from_title_field(self, notion_tools):
        """Test title extraction from title field."""
        # Arrange
        notion_object = {
            "title": [{"text": {"content": "Database Title"}}]
        }
        
        # Act
        title = notion_tools._extract_title(notion_object)
        
        # Assert
        assert title == "Database Title"
    
    def test_extract_title_fallback(self, notion_tools):
        """Test title extraction fallback to 'Untitled'."""
        # Arrange
        notion_object = {"properties": {}}
        
        # Act
        title = notion_tools._extract_title(notion_object)
        
        # Assert
        assert title == "Untitled"
    
    def test_extract_title_with_malformed_data(self, notion_tools):
        """Test title extraction with malformed data."""
        # Arrange
        notion_object = {
            "properties": {
                "Name": {
                    "title": []  # Empty title array
                }
            }
        }
        
        # Act
        title = notion_tools._extract_title(notion_object)
        
        # Assert
        assert title == "Untitled"

    @patch('src.tools.notion_tools.get_settings')
    def test_notion_tools_initialization(self, mock_get_settings):
        """Test NotionTools initialization."""
        # Arrange
        mock_settings = Mock()
        mock_settings.notion_integration_token = "test-token"
        mock_get_settings.return_value = mock_settings
        
        # Act
        with patch('src.tools.notion_tools.NotionClient') as mock_client_class:
            tools = NotionTools()
        
        # Assert
        mock_client_class.assert_called_once_with(auth="test-token")
        assert tools.client == mock_client_class.return_value

@pytest.mark.integration
class TestNotionToolsIntegration:
    """Integration tests for Notion tools (require real API keys)."""
    
    @pytest.mark.skip_if_no_api_keys
    def test_real_notion_search(self):
        """Test search with real Notion API (if configured)."""
        # This test would only run if real API keys are provided
        # and would test against a real Notion workspace
        tools = NotionTools()
        
        # This is just a placeholder - would need real test data
        # result = tools.search_pages("test")
        # assert isinstance(result, list)
        
        pytest.skip("Integration test requires real API configuration")
