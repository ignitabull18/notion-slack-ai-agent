"""
Test configuration and utilities.
"""

import pytest
import asyncio
from typing import Generator, AsyncGenerator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
from unittest.mock import Mock, AsyncMock

from src.main import app
from src.models.database import Base, get_db
from src.models.models import create_all_tables
from src.config import Settings, get_settings

# Test database URL (use SQLite for testing)
TEST_DATABASE_URL = "sqlite:///./test.db"

# Test settings
class TestSettings(Settings):
    """Test-specific settings."""
    database_url: str = TEST_DATABASE_URL
    debug: bool = True
    testing: bool = True
    metrics_enabled: bool = False
    
    # Use mock API keys for testing
    openai_api_key: str = "test-openai-key"
    notion_integration_token: str = "test-notion-token"
    slack_bot_token: str = "test-slack-token"
    slack_signing_secret: str = "test-slack-secret"
    api_secret_key: str = "test-secret-key"

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
def test_settings():
    """Provide test settings."""
    return TestSettings()

@pytest.fixture(scope="session")
def test_engine(test_settings):
    """Create a test database engine."""
    engine = create_engine(
        test_settings.database_url,
        connect_args={"check_same_thread": False}
    )
    return engine

@pytest.fixture(scope="session")
def test_db_session(test_engine):
    """Create test database session."""
    # Create all tables
    Base.metadata.create_all(bind=test_engine)
    
    TestingSessionLocal = sessionmaker(
        autocommit=False, 
        autoflush=False, 
        bind=test_engine
    )
    
    yield TestingSessionLocal

    # Clean up
    Base.metadata.drop_all(bind=test_engine)

@pytest.fixture
def db_session(test_db_session):
    """Provide a database session for tests."""
    session = test_db_session()
    try:
        yield session
    finally:
        session.rollback()
        session.close()

@pytest.fixture
def client(test_settings, db_session):
    """Create a test client."""
    def override_get_db():
        yield db_session
    
    def override_get_settings():
        return test_settings
    
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_settings] = override_get_settings
    
    with TestClient(app) as test_client:
        yield test_client
    
    # Clean up overrides
    app.dependency_overrides.clear()

@pytest.fixture
def mock_notion_client():
    """Mock Notion client for testing."""
    mock_client = Mock()
    
    # Mock common Notion API responses
    mock_client.pages.create.return_value = {
        "id": "test-page-id",
        "url": "https://notion.so/test-page",
        "properties": {}
    }
    
    mock_client.pages.retrieve.return_value = {
        "id": "test-page-id",
        "properties": {},
        "url": "https://notion.so/test-page"
    }
    
    mock_client.databases.query.return_value = {
        "results": [
            {
                "id": "test-page-id",
                "properties": {},
                "url": "https://notion.so/test-page",
                "created_time": "2023-01-01T00:00:00.000Z",
                "last_edited_time": "2023-01-01T00:00:00.000Z"
            }
        ]
    }
    
    mock_client.search.return_value = {
        "results": [
            {
                "id": "test-page-id",
                "object": "page",
                "url": "https://notion.so/test-page"
            }
        ]
    }
    
    return mock_client

@pytest.fixture
def mock_slack_client():
    """Mock Slack client for testing."""
    mock_client = AsyncMock()
    
    # Mock common Slack API responses
    mock_client.chat_postMessage.return_value = {
        "ok": True,
        "ts": "1234567890.123456",
        "channel": "C1234567890"
    }
    
    mock_client.conversations_info.return_value = {
        "ok": True,
        "channel": {
            "id": "C1234567890",
            "name": "general",
            "is_private": False,
            "num_members": 10
        }
    }
    
    mock_client.conversations_list.return_value = {
        "ok": True,
        "channels": [
            {
                "id": "C1234567890",
                "name": "general",
                "is_private": False,
                "num_members": 10
            }
        ]
    }
    
    mock_client.users_info.return_value = {
        "ok": True,
        "user": {
            "id": "U1234567890",
            "name": "testuser",
            "real_name": "Test User",
            "profile": {
                "email": "test@example.com"
            }
        }
    }
    
    return mock_client

@pytest.fixture
def mock_agent():
    """Mock AI agent for testing."""
    mock_agent = Mock()
    
    mock_response = Mock()
    mock_response.content = "Test agent response"
    mock_agent.run.return_value = mock_response
    
    return mock_agent

@pytest.fixture
def sample_notion_page():
    """Sample Notion page data for testing."""
    return {
        "id": "test-page-id-123",
        "properties": {
            "Name": {
                "title": [
                    {
                        "text": {
                            "content": "Test Page"
                        }
                    }
                ]
            },
            "Status": {
                "select": {
                    "name": "In Progress"
                }
            }
        },
        "url": "https://notion.so/test-page-123",
        "created_time": "2023-01-01T00:00:00.000Z",
        "last_edited_time": "2023-01-01T01:00:00.000Z"
    }

@pytest.fixture
def sample_slack_event():
    """Sample Slack event data for testing."""
    return {
        "type": "app_mention",
        "event": {
            "type": "app_mention",
            "user": "U1234567890",
            "text": "<@U0BOTUSER> create a task",
            "ts": "1234567890.123456",
            "channel": "C1234567890",
            "thread_ts": None
        },
        "team_id": "T1234567890",
        "api_app_id": "A1234567890",
        "event_id": "Ev1234567890",
        "event_time": 1234567890
    }

@pytest.fixture
def api_headers(test_settings):
    """Headers for API requests."""
    return {
        "Authorization": f"Bearer {test_settings.api_secret_key}",
        "Content-Type": "application/json"
    }

class TestDataFactory:
    """Factory for creating test data."""
    
    @staticmethod
    def create_agent_session_data(**kwargs):
        """Create agent session test data."""
        default_data = {
            "session_id": "test-session-123",
            "user_id": "U1234567890",
            "channel_id": "C1234567890",
            "context": {"test": True},
            "metadata": {"test_mode": True}
        }
        default_data.update(kwargs)
        return default_data
    
    @staticmethod
    def create_workflow_config_data(**kwargs):
        """Create workflow configuration test data."""
        default_data = {
            "name": "Test Workflow",
            "workflow_type": "sync_notion_to_slack",
            "source_config": {"database_id": "test-db-123"},
            "target_config": {"channel_id": "C1234567890"},
            "is_active": True
        }
        default_data.update(kwargs)
        return default_data
    
    @staticmethod
    def create_event_log_data(**kwargs):
        """Create event log test data."""
        default_data = {
            "event_type": "agent_response",
            "source": "agent",
            "event_data": {"test": True},
            "user_id": "U1234567890",
            "session_id": "test-session-123"
        }
        default_data.update(kwargs)
        return default_data
    
    @staticmethod
    def create_user_mapping_data(**kwargs):
        """Create user mapping test data."""
        default_data = {
            "slack_user_id": "U1234567890",
            "notion_user_id": "notion-user-123",
            "email": "test@example.com",
            "display_name": "Test User"
        }
        default_data.update(kwargs)
        return default_data

# Pytest markers
pytestmark = pytest.mark.asyncio

# Custom assertions
def assert_api_response_success(response):
    """Assert that an API response is successful."""
    assert response.status_code in [200, 201], f"Expected success status, got {response.status_code}: {response.text}"
    data = response.json()
    assert data.get("success") is not False, f"Response indicates failure: {data}"

def assert_api_response_error(response, expected_status=400):
    """Assert that an API response is an error."""
    assert response.status_code == expected_status, f"Expected status {expected_status}, got {response.status_code}"
    data = response.json()
    assert "error" in data or "detail" in data, f"Response should contain error information: {data}"

def assert_notion_page_structure(page_data):
    """Assert that page data has the expected Notion structure."""
    assert "id" in page_data
    assert "properties" in page_data
    assert "url" in page_data

def assert_slack_message_structure(message_data):
    """Assert that message data has the expected Slack structure."""
    assert "ts" in message_data
    assert "channel" in message_data
    assert "text" in message_data or "blocks" in message_data

# Test utilities
def create_test_api_key(db_session, **kwargs):
    """Create a test API key in the database."""
    from src.models.models import APIKeyModel
    from src.services.auth_service import auth_service
    
    key_id, api_key = auth_service.generate_api_key()
    key_hash = auth_service.hash_api_key(api_key)
    
    default_data = {
        "key_id": key_id,
        "key_hash": key_hash,
        "name": "Test API Key",
        "description": "For testing",
        "permissions": ["*"],
        "rate_limit": 1000,
        "is_active": True
    }
    default_data.update(kwargs)
    
    api_key_model = APIKeyModel(**default_data)
    db_session.add(api_key_model)
    db_session.commit()
    db_session.refresh(api_key_model)
    
    return api_key_model, api_key

async def wait_for_condition(condition_func, timeout=5.0, interval=0.1):
    """Wait for a condition to become true."""
    import time
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        if await condition_func() if asyncio.iscoroutinefunction(condition_func) else condition_func():
            return True
        await asyncio.sleep(interval)
    
    return False

# Test decorators
def skip_if_no_api_keys(func):
    """Skip test if no API keys are configured."""
    import os
    
    def wrapper(*args, **kwargs):
        if not os.environ.get("OPENAI_API_KEY") and not kwargs.get("mock_api_keys"):
            pytest.skip("No API keys configured for testing")
        return func(*args, **kwargs)
    
    return wrapper

def requires_database(func):
    """Mark test as requiring a database."""
    return pytest.mark.database(func)

def requires_external_apis(func):
    """Mark test as requiring external APIs."""
    return pytest.mark.external_api(func)

# Mock context managers
class MockAgent:
    """Mock agent context manager for testing."""
    
    def __init__(self, responses=None):
        self.responses = responses or ["Mock agent response"]
        self.call_count = 0
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass
    
    def run(self, message):
        response = Mock()
        response.content = self.responses[self.call_count % len(self.responses)]
        self.call_count += 1
        return response
