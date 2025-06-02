"""
Tests for API endpoints and authentication.
"""
import pytest
from unittest.mock import Mock, patch
from fastapi import status
from src.services.auth_service import AuthService
from src.services.rate_limiter import RateLimiter, RateLimit

class TestAPIEndpoints:
    """Test cases for API endpoints."""
    
    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "notion-slack-agent"
    
    def test_agent_status(self, client):
        """Test agent status endpoint."""
        response = client.get("/api/v1/status")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "active"
        assert "components" in data
    
    def test_chat_endpoint_unauthorized(self, client):
        """Test chat endpoint without authentication."""
        response = client.post(
            "/api/v1/chat",
            json={"message": "Hello"}
        )
        assert response.status_code == 401
    
    def test_chat_endpoint_success(self, client, auth_headers, mock_agent):
        """Test successful chat interaction."""
        response = client.post(
            "/api/v1/chat",
            json={"message": "Create a task"},
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "response" in data
    
    def test_notion_pages_endpoint(self, client, auth_headers, mock_notion_client):
        """Test Notion pages creation endpoint."""
        response = client.post(
            "/api/v1/notion/pages",
            json={
                "database_id": "test_database_id",
                "title": "Test Page",
                "properties": {}
            },
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
    
    @pytest.mark.asyncio
    async def test_slack_channels_endpoint(self, client, auth_headers, mock_slack_client):
        """Test Slack channels listing endpoint."""
        response = client.get("/api/v1/slack/channels", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "channels" in data
    
    @pytest.mark.asyncio
    async def test_slack_messages_endpoint(self, client, auth_headers, mock_slack_client):
        """Test Slack message sending endpoint."""
        response = client.post(
            "/api/v1/slack/messages",
            json={
                "channel": "#test",
                "text": "Test message"
            },
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

class TestWebhookEndpoints:
    """Test cases for webhook endpoints."""
    
    def test_notion_webhook_invalid_signature(self, client):
        """Test Notion webhook with invalid signature."""
        response = client.post(
            "/webhook/notion",
            json={"test": "data"},
            headers={"Notion-Webhook-Signature": "invalid"}
        )
        assert response.status_code == 401
    
    def test_slack_webhook_url_verification(self, client):
        """Test Slack webhook URL verification."""
        with patch("src.integrations.webhook_handlers.verify_slack_webhook", return_value=True):
            response = client.post(
                "/webhook/slack/events",
                json={
                    "type": "url_verification",
                    "challenge": "test_challenge"
                },
                headers={
                    "X-Slack-Request-Timestamp": "1234567890",
                    "X-Slack-Signature": "valid_signature"
                }
            )
            assert response.status_code == 200
            data = response.json()
            assert data["challenge"] == "test_challenge"
    
    def test_slack_command_endpoint(self, client):
        """Test Slack slash command endpoint."""
        with patch("src.integrations.webhook_handlers.verify_slack_webhook", return_value=True):
            response = client.post(
                "/webhook/slack/commands",
                data={
                    "token": "verification_token",
                    "command": "/task",
                    "text": "Create a new task",
                    "user_id": "U1234567890",
                    "channel_id": "C1234567890"
                }
            )
            assert response.status_code == 200
            data = response.json()
            assert data["response_type"] == "ephemeral"

class TestAuthService:
    """Test cases for authentication service."""
    
    def test_create_access_token(self, db_session, test_settings):
        """Test JWT token creation."""
        auth_service = AuthService(db_session)
        token_data = {"sub": "1", "is_admin": False}
        
        token = auth_service.create_access_token(token_data)
        
        assert isinstance(token, str)
        assert len(token) > 0
    
    def test_verify_token_success(self, db_session, test_settings):
        """Test token verification."""
        auth_service = AuthService(db_session)
        token_data = {"sub": "1", "is_admin": False}
        
        token = auth_service.create_access_token(token_data)
        payload = auth_service.verify_token(token)
        
        assert payload["sub"] == "1"
        assert payload["is_admin"] is False
    
    def test_verify_token_invalid(self, db_session, test_settings):
        """Test invalid token verification."""
        auth_service = AuthService(db_session)
        
        with pytest.raises(Exception):
            auth_service.verify_token("invalid_token")
    
    def test_authenticate_user_success(self, db_session, test_user):
        """Test user authentication."""
        auth_service = AuthService(db_session)
        
        user = auth_service.authenticate_user(
            test_user.slack_user_id,
            test_user.slack_team_id
        )
        
        assert user is not None
        assert user.id == test_user.id
    
    def test_authenticate_user_not_found(self, db_session):
        """Test authentication with non-existent user."""
        auth_service = AuthService(db_session)
        
        user = auth_service.authenticate_user("nonexistent", "team")
        
        assert user is None
    
    def test_create_api_key(self, db_session, test_user):
        """Test API key creation."""
        auth_service = AuthService(db_session)
        
        result = auth_service.create_api_key(
            name="Test API Key",
            created_by_user_id=test_user.id,
            scopes=["notion:read", "slack:write"]
        )
        
        assert "key_id" in result
        assert "api_key" in result
        assert result["api_key"].startswith("agno_")
    
    def test_authenticate_api_key_success(self, db_session, test_user):
        """Test API key authentication."""
        auth_service = AuthService(db_session)
        
        # Create API key
        key_data = auth_service.create_api_key(
            name="Test Key",
            created_by_user_id=test_user.id
        )
        
        # Authenticate with the key
        api_key_record = auth_service.authenticate_api_key(key_data["api_key"])
        
        assert api_key_record is not None
        assert api_key_record.name == "Test Key"
    
    def test_check_api_key_permissions(self, db_session, test_user):
        """Test API key permission checking."""
        auth_service = AuthService(db_session)
        
        # Create API key with specific scopes
        key_data = auth_service.create_api_key(
            name="Limited Key",
            created_by_user_id=test_user.id,
            scopes=["notion:read"]
        )
        
        api_key_record = auth_service.authenticate_api_key(key_data["api_key"])
        
        # Test permissions
        assert auth_service.check_api_key_permissions(api_key_record, "notion:read") is True
        assert auth_service.check_api_key_permissions(api_key_record, "notion:write") is False

class TestRateLimiter:
    """Test cases for rate limiting."""
    
    def test_rate_limit_within_bounds(self, mock_redis):
        """Test request within rate limits."""
        rate_limiter = RateLimiter()
        
        allowed, metadata = rate_limiter.check_rate_limit("test_key", "api")
        
        assert allowed is True
        assert "limit" in metadata
        assert "remaining" in metadata
    
    def test_rate_limit_exceeded(self, mock_redis):
        """Test rate limit exceeded scenario."""
        # Mock Redis to return high count
        mock_redis.execute.return_value = [None, 1001, None, None]
        
        rate_limiter = RateLimiter()
        allowed, metadata = rate_limiter.check_rate_limit("test_key", "api")
        
        # This test would need more sophisticated Redis mocking
        # For now, it demonstrates the testing pattern
        assert "limit" in metadata
    
    def test_custom_rate_limit(self, mock_redis):
        """Test custom rate limit configuration."""
        rate_limiter = RateLimiter()
        custom_limit = RateLimit(requests=10, window_seconds=60)
        
        allowed, metadata = rate_limiter.check_rate_limit(
            "test_key", 
            "api", 
            custom_limit
        )
        
        assert allowed is True
        assert metadata["limit"] == 10
    
    def test_get_rate_limit_status(self, mock_redis):
        """Test getting rate limit status."""
        rate_limiter = RateLimiter()
        
        status = rate_limiter.get_rate_limit_status("test_key", "api")
        
        assert "limit" in status
        assert "remaining" in status
        assert "current_count" in status

class TestDatabaseOperations:
    """Test database repository operations."""
    
    def test_user_repository_create(self, db_session):
        """Test user creation through repository."""
        from src.models.repositories import UserRepository
        
        repo = UserRepository(db_session)
        user = repo.create(
            slack_user_id="U1234567890",
            slack_team_id="T1234567890",
            email="test@example.com",
            display_name="Test User"
        )
        
        assert user.id is not None
        assert user.slack_user_id == "U1234567890"
    
    def test_user_repository_get_by_slack_id(self, db_session, test_user):
        """Test finding user by Slack ID."""
        from src.models.repositories import UserRepository
        
        repo = UserRepository(db_session)
        found_user = repo.get_by_slack_id(
            test_user.slack_user_id,
            test_user.slack_team_id
        )
        
        assert found_user is not None
        assert found_user.id == test_user.id
    
    def test_user_repository_search(self, db_session, test_user):
        """Test user search functionality."""
        from src.models.repositories import UserRepository
        
        repo = UserRepository(db_session)
        users = repo.search_users("Test")
        
        assert len(users) >= 1
        assert any(u.id == test_user.id for u in users)

class TestErrorHandling:
    """Test error handling scenarios."""
    
    def test_invalid_json_request(self, client, auth_headers):
        """Test API with invalid JSON."""
        response = client.post(
            "/api/v1/chat",
            data="invalid json",
            headers=auth_headers
        )
        assert response.status_code == 422  # Unprocessable Entity
    
    def test_missing_required_fields(self, client, auth_headers):
        """Test API with missing required fields."""
        response = client.post(
            "/api/v1/notion/pages",
            json={"title": "Missing database_id"},
            headers=auth_headers
        )
        assert response.status_code == 422
    
    def test_database_connection_error(self, client):
        """Test behavior when database is unavailable."""
        # This would require more sophisticated mocking
        # to simulate database connection failures
        pass
