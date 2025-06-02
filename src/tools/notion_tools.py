"""
Notion-specific tools for the AI agent.
"""
import asyncio
from typing import List, Dict, Any, Optional
from agno.tools import Tool
from notion_client import Client as NotionClient
from src.config import get_settings

class NotionTools(Tool):
    """Tools for interacting with Notion API."""

    def __init__(self):
        super().__init__()
        settings = get_settings()
        self.client = NotionClient(auth=settings.notion_integration_token)

    def create_page(self, 
                   parent_database_id: str,
                   title: str,
                   properties: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new page in a Notion database."""
        try:
            page_data = {
                "parent": {"database_id": parent_database_id},
                "properties": {
                    "Name": {
                        "title": [{"text": {"content": title}}]
                    },
                    **properties
                }
            }

            response = self.client.pages.create(**page_data)
            return {
                "success": True,
                "page_id": response["id"],
                "url": response["url"],
                "message": f"Created page: {title}"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to create page: {title}"
            }

    def query_database(self, 
                      database_id: str, 
                      filter_conditions: Optional[Dict] = None,
                      sorts: Optional[List[Dict]] = None) -> List[Dict]:
        """Query a Notion database with optional filters and sorting."""
        try:
            query_params = {"database_id": database_id}
            if filter_conditions:
                query_params["filter"] = filter_conditions
            if sorts:
                query_params["sorts"] = sorts

            response = self.client.databases.query(**query_params)
            return [{
                "id": page["id"],
                "properties": page["properties"],
                "url": page["url"],
                "created_time": page["created_time"],
                "last_edited_time": page["last_edited_time"]
            } for page in response["results"]]
        except Exception as e:
            return [{"error": str(e)}]

    def update_page(self, page_id: str, properties: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing Notion page."""
        try:
            response = self.client.pages.update(
                page_id=page_id,
                properties=properties
            )
            return {
                "success": True,
                "page_id": response["id"],
                "message": "Page updated successfully"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to update page"
            }

    def get_page(self, page_id: str) -> Dict[str, Any]:
        """Get a specific Notion page by ID."""
        try:
            response = self.client.pages.retrieve(page_id)
            return {
                "success": True,
                "page": {
                    "id": response["id"],
                    "properties": response["properties"],
                    "url": response["url"],
                    "created_time": response["created_time"],
                    "last_edited_time": response["last_edited_time"]
                }
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to get page: {page_id}"
            }

    def append_block_children(self, 
                             block_id: str, 
                             children: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Append block children to a page or block."""
        try:
            response = self.client.blocks.children.append(
                block_id=block_id,
                children=children
            )
            return {
                "success": True,
                "results": response["results"],
                "message": "Blocks appended successfully"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to append blocks"
            }

    def search_pages(self, 
                    query: str, 
                    filter_type: Optional[str] = None) -> List[Dict]:
        """Search for pages in the workspace."""
        try:
            search_params = {"query": query}
            if filter_type:
                search_params["filter"] = {"property": "object", "value": filter_type}
            
            response = self.client.search(**search_params)
            return [{
                "id": result["id"],
                "object": result["object"],
                "url": result.get("url", ""),
                "title": self._extract_title(result),
                "last_edited_time": result.get("last_edited_time", "")
            } for result in response["results"]]
        except Exception as e:
            return [{"error": str(e)}]

    def get_database_schema(self, database_id: str) -> Dict[str, Any]:
        """Get the schema/structure of a Notion database."""
        try:
            response = self.client.databases.retrieve(database_id)
            return {
                "success": True,
                "database": {
                    "id": response["id"],
                    "title": self._extract_title(response),
                    "properties": response["properties"],
                    "url": response["url"]
                }
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to get database schema: {database_id}"
            }

    def _extract_title(self, notion_object: Dict[str, Any]) -> str:
        """Extract title from a Notion object."""
        try:
            if "properties" in notion_object and "Name" in notion_object["properties"]:
                title_prop = notion_object["properties"]["Name"]
                if "title" in title_prop and title_prop["title"]:
                    return title_prop["title"][0]["text"]["content"]
            elif "title" in notion_object and notion_object["title"]:
                return notion_object["title"][0]["text"]["content"]
            return "Untitled"
        except (KeyError, IndexError, TypeError):
            return "Untitled"
