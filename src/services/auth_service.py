"""
Authentication and authorization service for the Notion-Slack AI Agent.
"""
import hashlib
import secrets
import hmac
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from src.config import get_settings
from src.models.repositories import UserRepository, APIKeyRepository
from src.models.schemas import User, APIKey
from src.utils.errors import AuthenticationError, ValidationError

settings = get_settings()

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT settings
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

class AuthService:
    """Authentication and authorization service."""
    
    def __init__(self, db: Session):
        self.db = db
        self.user_repo = UserRepository(db)
        self.api_key_repo = APIKeyRepository(db)
    
    def create_access_token(self, data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """
        Create JWT access token.
        
        Args:
            data: Token payload data
            expires_delta: Token expiration time
        
        Returns:
            JWT token string
        """
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, settings.api_secret_key, algorithm=ALGORITHM)
        return encoded_jwt
    
    def verify_token(self, token: str) -> Dict[str, Any]:
        """
        Verify JWT token and return payload.
        
        Args:
            token: JWT token string
        
        Returns:
            Token payload
        
        Raises:
            AuthenticationError: If token is invalid
        """
        try:
            payload = jwt.decode(token, settings.api_secret_key, algorithms=[ALGORITHM])
            return payload
        except JWTError:
            raise AuthenticationError("Invalid token")
    
    def authenticate_user(self, slack_user_id: str, slack_team_id: str) -> Optional[User]:
        """
        Authenticate user by Slack credentials.
        
        Args:
            slack_user_id: Slack user ID
            slack_team_id: Slack team ID
        
        Returns:
            User object if authenticated, None otherwise
        """
        user = self.user_repo.get_by_slack_id(slack_user_id, slack_team_id)
        if user and user.is_active:
            # Update last seen timestamp
            self.user_repo.update_last_seen(user.id)
            return user
        return None
    
    def create_user_token(self, user: User) -> str:
        """
        Create access token for user.
        
        Args:
            user: User object
        
        Returns:
            JWT token string
        """
        token_data = {
            "sub": str(user.id),
            "slack_user_id": user.slack_user_id,
            "slack_team_id": user.slack_team_id,
            "is_admin": user.is_admin
        }
        return self.create_access_token(token_data)
    
    def get_current_user(self, token: str) -> User:
        """
        Get current user from token.
        
        Args:
            token: JWT token string
        
        Returns:
            User object
        
        Raises:
            AuthenticationError: If user not found or inactive
        """
        try:
            payload = self.verify_token(token)
            user_id = int(payload.get("sub"))
            if user_id is None:
                raise AuthenticationError("Invalid token payload")
        except (JWTError, ValueError):
            raise AuthenticationError("Invalid token")
        
        user = self.user_repo.get_by_id(user_id)
        if user is None or not user.is_active:
            raise AuthenticationError("User not found or inactive")
        
        return user
    
    def create_api_key(self, name: str, created_by_user_id: int, 
                      scopes: List[str] = None, 
                      rate_limit_per_hour: int = 1000,
                      expires_days: int = None) -> Dict[str, str]:
        """
        Create new API key.
        
        Args:
            name: API key name
            created_by_user_id: ID of user creating the key
            scopes: List of allowed scopes
            rate_limit_per_hour: Hourly rate limit
            expires_days: Days until expiration (None for no expiration)
        
        Returns:
            Dictionary with key_id and api_key
        """
        # Generate API key
        api_key = f"agno_{secrets.token_urlsafe(32)}"
        key_id = secrets.token_urlsafe(16)
        
        # Hash the API key for storage
        key_hash = self._hash_api_key(api_key)
        
        # Calculate expiration
        expires_at = None
        if expires_days:
            expires_at = datetime.utcnow() + timedelta(days=expires_days)
        
        # Create API key record
        api_key_record = APIKey(
            key_id=key_id,
            key_hash=key_hash,
            name=name,
            created_by_user_id=created_by_user_id,
            scopes=scopes or [],
            rate_limit_per_hour=rate_limit_per_hour,
            expires_at=expires_at
        )
        
        self.db.add(api_key_record)
        self.db.commit()
        
        return {
            "key_id": key_id,
            "api_key": api_key
        }
    
    def authenticate_api_key(self, api_key: str) -> Optional[APIKey]:
        """
        Authenticate API key.
        
        Args:
            api_key: API key string
        
        Returns:
            APIKey object if valid, None otherwise
        """
        # Extract key ID from API key
        if not api_key.startswith("agno_"):
            return None
        
        # Hash the provided key
        key_hash = self._hash_api_key(api_key)
        
        # Find matching API key
        api_key_record = self.db.query(APIKey).filter(
            APIKey.key_hash == key_hash,
            APIKey.is_active == True
        ).first()
        
        if not api_key_record:
            return None
        
        # Check expiration
        if api_key_record.expires_at and api_key_record.expires_at < datetime.utcnow():
            return None
        
        # Update usage statistics
        self.api_key_repo.update_usage(api_key_record.key_id)
        
        return api_key_record
    
    def check_api_key_permissions(self, api_key: APIKey, required_scope: str) -> bool:
        """
        Check if API key has required permissions.
        
        Args:
            api_key: APIKey object
            required_scope: Required scope/permission
        
        Returns:
            True if authorized, False otherwise
        """
        if not api_key.scopes:
            # No scopes means full access (for backwards compatibility)
            return True
        
        return required_scope in api_key.scopes or "admin" in api_key.scopes
    
    def check_rate_limit(self, api_key: APIKey) -> bool:
        """
        Check if API key is within rate limits.
        
        Args:
            api_key: APIKey object
        
        Returns:
            True if within limits, False otherwise
        """
        return api_key.current_hour_requests < api_key.rate_limit_per_hour
    
    def revoke_api_key(self, key_id: str, user_id: int) -> bool:
        """
        Revoke API key.
        
        Args:
            key_id: API key ID to revoke
            user_id: ID of user requesting revocation
        
        Returns:
            True if revoked successfully, False otherwise
        """
        api_key = self.api_key_repo.get_by_key_id(key_id)
        if not api_key:
            return False
        
        # Check if user has permission to revoke
        user = self.user_repo.get_by_id(user_id)
        if not user:
            return False
        
        if api_key.created_by_user_id != user_id and not user.is_admin:
            return False
        
        # Revoke the key
        api_key.is_active = False
        api_key.updated_at = datetime.utcnow()
        self.db.commit()
        
        return True
    
    def verify_slack_signature(self, body: bytes, timestamp: str, signature: str) -> bool:
        """
        Verify Slack webhook signature.
        
        Args:
            body: Request body bytes
            timestamp: Request timestamp
            signature: Slack signature header
        
        Returns:
            True if signature is valid, False otherwise
        """
        # Check timestamp to prevent replay attacks
        request_time = int(timestamp)
        current_time = int(datetime.utcnow().timestamp())
        
        if abs(current_time - request_time) > 60 * 5:  # 5 minutes
            return False
        
        # Create signature base string
        sig_basestring = f"v0:{timestamp}:{body.decode()}"
        
        # Calculate expected signature
        expected_signature = 'v0=' + hmac.new(
            settings.slack_signing_secret.encode(),
            sig_basestring.encode(),
            hashlib.sha256
        ).hexdigest()
        
        # Compare signatures
        return hmac.compare_digest(signature, expected_signature)
    
    def verify_notion_signature(self, body: bytes, signature: str) -> bool:
        """
        Verify Notion webhook signature.
        
        Args:
            body: Request body bytes
            signature: Notion signature header
        
        Returns:
            True if signature is valid, False otherwise
        """
        expected_signature = hmac.new(
            settings.notion_webhook_secret.encode(),
            body,
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(signature, expected_signature)
    
    def _hash_api_key(self, api_key: str) -> str:
        """Hash API key for secure storage."""
        return hashlib.sha256(api_key.encode()).hexdigest()
    
    def get_user_permissions(self, user: User) -> List[str]:
        """
        Get user permissions/scopes.
        
        Args:
            user: User object
        
        Returns:
            List of permission scopes
        """
        permissions = ["user"]  # Base permission
        
        if user.is_admin:
            permissions.extend(["admin", "manage_users", "manage_api_keys"])
        
        # Add more granular permissions based on user roles/preferences
        permissions.extend([
            "notion:read", "notion:write",
            "slack:read", "slack:write",
            "workflows:execute"
        ])
        
        return permissions

class RoleBasedAccessControl:
    """Role-based access control utilities."""
    
    # Define permission scopes
    SCOPES = {
        "user": "Basic user access",
        "admin": "Administrative access",
        "notion:read": "Read Notion data",
        "notion:write": "Write Notion data", 
        "slack:read": "Read Slack data",
        "slack:write": "Write Slack data",
        "workflows:execute": "Execute workflows",
        "api:manage": "Manage API keys",
        "users:manage": "Manage users",
        "metrics:read": "Read system metrics"
    }
    
    # Define role hierarchies
    ROLES = {
        "user": ["user", "notion:read", "slack:read"],
        "power_user": ["user", "notion:read", "notion:write", "slack:read", "slack:write", "workflows:execute"],
        "admin": ["admin"] + list(SCOPES.keys())
    }
    
    @classmethod
    def get_role_permissions(cls, role: str) -> List[str]:
        """Get permissions for a role."""
        return cls.ROLES.get(role, [])
    
    @classmethod
    def has_permission(cls, user_permissions: List[str], required_permission: str) -> bool:
        """Check if user has required permission."""
        return required_permission in user_permissions or "admin" in user_permissions
    
    @classmethod
    def require_permission(cls, required_permission: str):
        """Decorator to require specific permission."""
        def decorator(func):
            def wrapper(*args, **kwargs):
                # This would be implemented with FastAPI dependencies
                # For now, it's a placeholder
                return func(*args, **kwargs)
            return wrapper
        return decorator

def get_password_hash(password: str) -> str:
    """Hash password using bcrypt."""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash."""
    return pwd_context.verify(plain_password, hashed_password)

def generate_secure_token(length: int = 32) -> str:
    """Generate cryptographically secure random token."""
    return secrets.token_urlsafe(length)
