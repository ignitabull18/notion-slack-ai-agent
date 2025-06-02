"""
Authentication and authorization services.
"""
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from fastapi.security import HTTPBearer
import logging

from src.models.database import get_db_session
from src.models.models import APIKeyModel, UserMappingModel
from src.models.repositories import user_mapping_repo
from src.utils.errors import AuthenticationError, ValidationError
from src.utils.helpers import mask_sensitive_data
from src.config import get_settings

logger = logging.getLogger(__name__)

class AuthService:
    """Authentication and authorization service."""
    
    def __init__(self):
        self.settings = get_settings()
    
    def generate_api_key(self) -> tuple[str, str]:
        """
        Generate a new API key.
        
        Returns:
            Tuple of (key_id, api_key)
        """
        # Generate key ID (public identifier)
        key_id = f"ak_{secrets.token_urlsafe(16)}"
        
        # Generate API key (secret)
        api_key = f"sk_{secrets.token_urlsafe(32)}"
        
        return key_id, api_key
    
    def hash_api_key(self, api_key: str) -> str:
        """
        Hash an API key for secure storage.
        
        Args:
            api_key: The API key to hash
            
        Returns:
            Hashed API key
        """
        return hashlib.sha256(api_key.encode()).hexdigest()
    
    def create_api_key(
        self,
        name: str,
        description: str = "",
        permissions: Optional[List[str]] = None,
        rate_limit: int = 1000,
        expires_in_days: Optional[int] = None,
        created_by: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new API key.
        
        Args:
            name: Name for the API key
            description: Description of the API key
            permissions: List of allowed operations
            rate_limit: Requests per hour limit
            expires_in_days: Expiration in days (None for no expiration)
            created_by: User who created the key
            
        Returns:
            Dictionary with key information
        """
        try:
            key_id, api_key = self.generate_api_key()
            key_hash = self.hash_api_key(api_key)
            
            expires_at = None
            if expires_in_days:
                expires_at = datetime.utcnow() + timedelta(days=expires_in_days)
            
            db = get_db_session()
            try:
                api_key_model = APIKeyModel(
                    key_id=key_id,
                    key_hash=key_hash,
                    name=name,
                    description=description,
                    permissions=permissions or [],
                    rate_limit=rate_limit,
                    created_by=created_by,
                    expires_at=expires_at
                )
                
                db.add(api_key_model)
                db.commit()
                db.refresh(api_key_model)
                
                logger.info(f"Created API key: {mask_sensitive_data(key_id)}")
                
                return {
                    "key_id": key_id,
                    "api_key": api_key,  # Only returned once!
                    "name": name,
                    "permissions": permissions or [],
                    "rate_limit": rate_limit,
                    "expires_at": expires_at.isoformat() if expires_at else None,
                    "created_at": api_key_model.created_at.isoformat()
                }
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Failed to create API key: {e}")
            raise AuthenticationError(f"Failed to create API key: {e}")
    
    def validate_api_key(self, api_key: str) -> Optional[APIKeyModel]:
        """
        Validate an API key and return the associated model.
        
        Args:
            api_key: The API key to validate
            
        Returns:
            APIKeyModel if valid, None otherwise
        """
        try:
            key_hash = self.hash_api_key(api_key)
            
            db = get_db_session()
            try:
                api_key_model = db.query(APIKeyModel).filter(
                    APIKeyModel.key_hash == key_hash,
                    APIKeyModel.is_active == True
                ).first()
                
                if not api_key_model:
                    return None
                
                # Check expiration
                if api_key_model.expires_at and api_key_model.expires_at < datetime.utcnow():
                    logger.warning(f"Expired API key used: {mask_sensitive_data(api_key_model.key_id)}")
                    return None
                
                # Update last used timestamp
                api_key_model.last_used = datetime.utcnow()
                db.commit()
                
                return api_key_model
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Error validating API key: {e}")
            return None
    
    def check_permission(self, api_key_model: APIKeyModel, required_permission: str) -> bool:
        """
        Check if an API key has the required permission.
        
        Args:
            api_key_model: The API key model
            required_permission: Required permission string
            
        Returns:
            True if permission granted, False otherwise
        """
        # If no permissions are set, allow all (for backwards compatibility)
        if not api_key_model.permissions:
            return True
        
        # Check for wildcard permission
        if "*" in api_key_model.permissions:
            return True
        
        # Check for specific permission
        return required_permission in api_key_model.permissions
    
    def revoke_api_key(self, key_id: str) -> bool:
        """
        Revoke an API key.
        
        Args:
            key_id: The key ID to revoke
            
        Returns:
            True if successfully revoked, False otherwise
        """
        try:
            db = get_db_session()
            try:
                api_key_model = db.query(APIKeyModel).filter(
                    APIKeyModel.key_id == key_id
                ).first()
                
                if api_key_model:
                    api_key_model.is_active = False
                    db.commit()
                    
                    logger.info(f"Revoked API key: {mask_sensitive_data(key_id)}")
                    return True
                
                return False
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Failed to revoke API key {mask_sensitive_data(key_id)}: {e}")
            return False
    
    def list_api_keys(self, created_by: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List API keys (without the actual key values).
        
        Args:
            created_by: Filter by creator (optional)
            
        Returns:
            List of API key information
        """
        try:
            db = get_db_session()
            try:
                query = db.query(APIKeyModel).filter(APIKeyModel.is_active == True)
                
                if created_by:
                    query = query.filter(APIKeyModel.created_by == created_by)
                
                api_keys = query.all()
                
                return [
                    {
                        "key_id": key.key_id,
                        "name": key.name,
                        "description": key.description,
                        "permissions": key.permissions,
                        "rate_limit": key.rate_limit,
                        "created_by": key.created_by,
                        "created_at": key.created_at.isoformat(),
                        "last_used": key.last_used.isoformat() if key.last_used else None,
                        "expires_at": key.expires_at.isoformat() if key.expires_at else None
                    }
                    for key in api_keys
                ]
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Failed to list API keys: {e}")
            return []

class SlackAuthService:
    """Slack-specific authentication service."""
    
    def __init__(self):
        self.settings = get_settings()
    
    def verify_slack_request(
        self, 
        body: bytes, 
        timestamp: str, 
        signature: str
    ) -> bool:
        """
        Verify Slack request signature.
        
        Args:
            body: Request body
            timestamp: Slack timestamp header
            signature: Slack signature header
            
        Returns:
            True if signature is valid, False otherwise
        """
        try:
            import hmac
            import hashlib
            
            # Check timestamp to prevent replay attacks
            request_timestamp = int(timestamp)
            current_timestamp = int(datetime.utcnow().timestamp())
            
            if abs(current_timestamp - request_timestamp) > 300:  # 5 minutes
                logger.warning("Slack request timestamp too old")
                return False
            
            # Verify signature
            sig_basestring = f"v0:{timestamp}:{body.decode()}"
            expected_signature = 'v0=' + hmac.new(
                self.settings.slack_signing_secret.encode(),
                sig_basestring.encode(),
                hashlib.sha256
            ).hexdigest()
            
            return hmac.compare_digest(signature, expected_signature)
            
        except Exception as e:
            logger.error(f"Error verifying Slack request: {e}")
            return False
    
    def get_or_create_user_mapping(
        self, 
        slack_user_id: str,
        user_info: Optional[Dict[str, Any]] = None
    ) -> Optional[UserMappingModel]:
        """
        Get or create user mapping for Slack user.
        
        Args:
            slack_user_id: Slack user ID
            user_info: Optional user information from Slack API
            
        Returns:
            UserMappingModel or None
        """
        try:
            db = get_db_session()
            try:
                # Try to get existing mapping
                user_mapping = user_mapping_repo.get_by_slack_user_id(db, slack_user_id)
                
                if user_mapping:
                    # Update last seen
                    user_mapping_repo.update_last_seen(db, slack_user_id)
                    return user_mapping
                
                # Create new mapping if user_info is provided
                if user_info:
                    from src.models.schemas import UserMappingCreate
                    
                    create_data = UserMappingCreate(
                        slack_user_id=slack_user_id,
                        email=user_info.get("profile", {}).get("email"),
                        display_name=user_info.get("real_name") or user_info.get("name"),
                        preferences={}
                    )
                    
                    user_mapping = user_mapping_repo.create(db, create_data)
                    logger.info(f"Created user mapping for Slack user: {mask_sensitive_data(slack_user_id)}")
                    return user_mapping
                
                return None
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Error getting/creating user mapping: {e}")
            return None

class PermissionService:
    """Permission management service."""
    
    # Define available permissions
    PERMISSIONS = {
        "agent.chat": "Chat with AI agent",
        "agent.status": "View agent status",
        "notion.read": "Read Notion data",
        "notion.write": "Write to Notion",
        "slack.read": "Read Slack data", 
        "slack.write": "Send Slack messages",
        "workflow.read": "View workflows",
        "workflow.write": "Create/modify workflows",
        "workflow.execute": "Execute workflows",
        "admin.users": "Manage users",
        "admin.keys": "Manage API keys",
        "admin.system": "System administration"
    }
    
    @classmethod
    def get_all_permissions(cls) -> Dict[str, str]:
        """Get all available permissions."""
        return cls.PERMISSIONS.copy()
    
    @classmethod
    def validate_permissions(cls, permissions: List[str]) -> List[str]:
        """
        Validate a list of permissions.
        
        Args:
            permissions: List of permission strings
            
        Returns:
            List of valid permissions
            
        Raises:
            ValidationError: If invalid permissions found
        """
        invalid_permissions = [p for p in permissions if p not in cls.PERMISSIONS and p != "*"]
        
        if invalid_permissions:
            raise ValidationError(
                f"Invalid permissions: {invalid_permissions}",
                field="permissions"
            )
        
        return permissions

# Service instances
auth_service = AuthService()
slack_auth_service = SlackAuthService()
permission_service = PermissionService()

# Security dependencies for FastAPI
security = HTTPBearer()

def get_current_api_key(api_key: str) -> APIKeyModel:
    """
    FastAPI dependency to get current API key.
    
    Args:
        api_key: API key from Authorization header
        
    Returns:
        APIKeyModel
        
    Raises:
        HTTPException: If authentication fails
    """
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required"
        )
    
    api_key_model = auth_service.validate_api_key(api_key)
    if not api_key_model:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )
    
    return api_key_model

def require_permission(permission: str):
    """
    FastAPI dependency factory for permission checking.
    
    Args:
        permission: Required permission string
        
    Returns:
        Dependency function
    """
    def check_permission(api_key_model: APIKeyModel = None) -> APIKeyModel:
        if not api_key_model:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )
        
        if not auth_service.check_permission(api_key_model, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission required: {permission}"
            )
        
        return api_key_model
    
    return check_permission
