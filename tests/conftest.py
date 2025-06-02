"""
Test configuration and fixtures for the Notion-Slack AI Agent tests.
"""
import pytest
import asyncio
from typing import Generator
from unittest.mock import Mock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from src.main import app
from src.models.database import Base, get_db
from src.models.schemas import User, UserPreferences
from src.config import Settings, get_settings

# Test database URL (in-memory SQLite)
TEST_DATABASE_URL = "sqlite:///./test.db"

# Create test engine
test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False}
)

# Test session factory
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="function")
def db_session():
    """Create a test database session."""
    # Create tables
    Base.metadata.create_all(bind=test_engine)
    
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        # Drop tables after each test
        Base.metadata.drop_all(bind=test_engine)

@pytest.fixture(scope="function")
def test_settings():
    """Create test settings."""
    return Settings(
        environment="test",
        debug=True,
        database_url=TEST_DATABASE_URL,
        api_secret_key="test_secret_key_12345678901234567890",
        openai_api_key="test_openai_key",
        notion_integration_token="test_notion_token",
        slack_bot_token="test_slack_token",
        slack_signing_secret="test_slack_secret",
        notion_webhook_secret="test_notion_webhook_secret",
        redis_url="redis://localhost:6379/1"  # Use different DB for tests
    )

@pytest.fixture(scope="function")
def client(db_session, test_settings):
    """Create a test client."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    def override_get_settings():
        return test_settings
    
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_settings] = override_get_settings
    
    with TestClient(app) as test_client:
        yield test_client
    
    # Clean up
    app.dependency_overrides.clear()

@pytest.fixture
def test_user(db_session):
    """Create a test user."""
    user = User(
        slack_user_id="U1234567890",
        slack_team_id="T1234567890",
        email="test@example.com",
        display_name="Test User",
        real_name="Test User",
        is_active=True,
        is_admin=False
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user

@pytest.fixture
def test_admin_user(db_session):
    """Create a test admin user."""
    user = User(
        slack_user_id="U0987654321",
        slack_team_id="T1234567890",
        email="admin@example.com",
        display_name="Admin User",
        real_name="Admin User",
        is_active=True,
        is_admin=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user

@pytest.fixture
def mock_notion_client():
    """Mock Notion client."""
    with patch("src.tools.notion_tools.NotionClient") as mock:
        mock_instance = Mock()
        mock.return_value = mock_instance
        
        # Configure mock responses
        mock_instance.pages.create.return_value = {
            "id": "test_page_id",
            "url": "https://notion.so/test_page",
            "properties": {}
        }
        
        mock_instance.databases.query.return_value = {
            "results": [
                {
                    "id": "test_page_id",
                    "properties": {"Name": {"title": [{"text": {"content": "Test Page"}}]}},
                    "url": "https://notion.so/test_page",
                    "created_time": "2023-01-01T00:00:00.000Z",
                    "last_edited_time": "2023-01-01T00:00:00.000Z"
                }
            ]
        }
        
        yield mock_instance

@pytest.fixture
def mock_slack_client():
    """Mock Slack client."""
    with patch("src.tools.slack_tools.AsyncWebClient") as mock:
        mock_instance = Mock()
        mock.return_value = mock_instance
        
        # Configure mock responses
        mock_instance.chat_postMessage.return_value = {
            "ok": True,
            "ts": "1234567890.123456",
            "channel": "C1234567890"
        }
        
        mock_instance.conversations_info.return_value = {
            "ok": True,
            "channel": {
                "id": "C1234567890",
                "name": "test-channel",
                "is_private": False,
                "num_members": 5,
                "topic": {"value": "Test channel"},
                "purpose": {"value": "For testing"}
            }
        }
        
        yield mock_instance

@pytest.fixture
def mock_redis():
    """Mock Redis client."""
    with patch("redis.from_url") as mock:
        mock_instance = Mock()
        mock.return_value = mock_instance
        
        # Configure mock responses
        mock_instance.pipeline.return_value = mock_instance
        mock_instance.execute.return_value = [None, 0, None, None]
        mock_instance.zcard.return_value = 0
        mock_instance.zrange.return_value = []
        
        yield mock_instance

@pytest.fixture
def sample_slack_event():
    """Sample Slack event payload."""
    return {
        "token": "verification_token",
        "team_id": "T1234567890",
        "api_app_id": "A1234567890",
        "event": {
            "type": "app_mention",
            "user": "U1234567890",
            "text": "<@U0987654321> hello there",
            "ts": "1234567890.123456",
            "channel": "C1234567890",
            "event_ts": "1234567890.123456"
        },
        "type": "event_callback",
        "event_id": "Ev1234567890",
        "event_time": 1234567890
    }

@pytest.fixture
def sample_notion_webhook():
    """Sample Notion webhook payload."""
    return {
        "object": "page",
        "id": "test_page_id",
        "created_time": "2023-01-01T00:00:00.000Z",
        "last_edited_time": "2023-01-01T00:00:00.000Z",
        "properties": {
            "Name": {
                "title": [
                    {
                        "text": {
                            "content": "Test Page"
                        }
                    }
                ]
            }
        },
        "url": "https://notion.so/test_page"
    }

@pytest.fixture
def auth_headers(test_settings):
    """Create authentication headers for API tests."""
    return {
        "Authorization": f"Bearer {test_settings.api_secret_key}",
        "Content-Type": "application/json"
    }

class MockAgentResponse:
    """Mock agent response for testing."""
    def __init__(self, content: str = "Test response"):
        self.content = content

@pytest.fixture
def mock_agent():
    """Mock Agno agent."""
    with patch("agno.agent.Agent") as mock:
        mock_instance = Mock()
        mock.return_value = mock_instance
        mock_instance.run.return_value = MockAgentResponse()
        yield mock_instance

# Helper functions for tests
def create_test_database_record(db_session, model_class, **kwargs):
    """Helper to create test database records."""
    record = model_class(**kwargs)
    db_session.add(record)
    db_session.commit()
    db_session.refresh(record)
    return record

def assert_response_success(response, expected_status=200):
    """Assert API response is successful."""
    assert response.status_code == expected_status
    data = response.json()
    assert "success" in data
    assert data["success"] is True
    return data

def assert_response_error(response, expected_status=400):
    """Assert API response contains error."""
    assert response.status_code == expected_status
    data = response.json()
    if "success" in data:
        assert data["success"] is False
    return data
