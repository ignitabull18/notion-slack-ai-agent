"""
SQLAlchemy database models.
"""
from sqlalchemy import (
    Column, Integer, String, DateTime, Boolean, Text, JSON, 
    ForeignKey, Index, Enum as SQLEnum, Float
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
import enum

from .database import Base
from .schemas import EventType, EventStatus, WorkflowType

class AgentSessionModel(Base):
    """Agent session tracking."""
    __tablename__ = "agent_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(255), unique=True, index=True, nullable=False)
    user_id = Column(String(255), index=True)
    channel_id = Column(String(255), index=True)
    context = Column(JSON, default=dict)
    metadata = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    last_activity = Column(DateTime(timezone=True), server_default=func.now())
    is_active = Column(Boolean, default=True, index=True)
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_session_user_active', 'user_id', 'is_active'),
        Index('idx_session_channel_active', 'channel_id', 'is_active'),
        Index('idx_session_last_activity', 'last_activity'),
    )

class WorkflowConfigModel(Base):
    """Workflow configuration storage."""
    __tablename__ = "workflow_configs"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    workflow_type = Column(SQLEnum(WorkflowType), nullable=False, index=True)
    source_config = Column(JSON, nullable=False)
    target_config = Column(JSON, nullable=False)
    schedule_config = Column(JSON)
    filters = Column(JSON)
    transformations = Column(JSON)
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    last_executed = Column(DateTime(timezone=True))
    execution_count = Column(Integer, default=0)
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_workflow_type_active', 'workflow_type', 'is_active'),
        Index('idx_workflow_schedule', 'is_active', 'schedule_config'),
    )

class EventLogModel(Base):
    """Event logging for audit and monitoring."""
    __tablename__ = "event_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    event_type = Column(SQLEnum(EventType), nullable=False, index=True)
    source = Column(String(100), nullable=False, index=True)
    event_data = Column(JSON, nullable=False)
    user_id = Column(String(255), index=True)
    session_id = Column(String(255), index=True)
    correlation_id = Column(String(255), index=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    status = Column(SQLEnum(EventStatus), default=EventStatus.COMPLETED, index=True)
    processing_time_ms = Column(Float)
    error_message = Column(Text)
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_event_type_timestamp', 'event_type', 'timestamp'),
        Index('idx_event_source_timestamp', 'source', 'timestamp'),
        Index('idx_event_status_timestamp', 'status', 'timestamp'),
        Index('idx_event_user_timestamp', 'user_id', 'timestamp'),
        Index('idx_event_session_timestamp', 'session_id', 'timestamp'),
        Index('idx_event_correlation', 'correlation_id'),
    )

class UserMappingModel(Base):
    """User mapping between Slack and Notion."""
    __tablename__ = "user_mappings"
    
    id = Column(Integer, primary_key=True, index=True)
    slack_user_id = Column(String(255), unique=True, nullable=False, index=True)
    notion_user_id = Column(String(255), index=True)
    email = Column(String(255), index=True)
    display_name = Column(String(255))
    preferences = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    last_seen = Column(DateTime(timezone=True))
    is_active = Column(Boolean, default=True, index=True)
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_user_slack_active', 'slack_user_id', 'is_active'),
        Index('idx_user_notion_active', 'notion_user_id', 'is_active'),
        Index('idx_user_email_active', 'email', 'is_active'),
    )

class IntegrationConfigModel(Base):
    """Configuration for external integrations."""
    __tablename__ = "integration_configs"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, nullable=False, index=True)
    integration_type = Column(String(100), nullable=False, index=True)  # notion, slack, etc.
    config_data = Column(JSON, nullable=False)
    credentials = Column(JSON)  # Encrypted sensitive data
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    last_tested = Column(DateTime(timezone=True))
    test_status = Column(String(50))  # success, failed, pending
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_integration_type_active', 'integration_type', 'is_active'),
    )

class WorkflowExecutionModel(Base):
    """Workflow execution tracking."""
    __tablename__ = "workflow_executions"
    
    id = Column(Integer, primary_key=True, index=True)
    workflow_id = Column(Integer, ForeignKey('workflow_configs.id'), nullable=False, index=True)
    execution_id = Column(String(255), unique=True, nullable=False, index=True)
    status = Column(SQLEnum(EventStatus), default=EventStatus.PENDING, index=True)
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True))
    duration_ms = Column(Float)
    items_processed = Column(Integer, default=0)
    errors = Column(JSON, default=list)
    result = Column(JSON)
    trigger_type = Column(String(100))  # manual, scheduled, webhook
    triggered_by = Column(String(255))  # user_id or system
    
    # Relationship
    workflow = relationship("WorkflowConfigModel", backref="executions")
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_execution_workflow_status', 'workflow_id', 'status'),
        Index('idx_execution_started', 'started_at'),
        Index('idx_execution_status_completed', 'status', 'completed_at'),
    )

class ConversationModel(Base):
    """Agent conversation storage."""
    __tablename__ = "conversations"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(255), ForeignKey('agent_sessions.session_id'), index=True)
    messages = Column(JSON, default=list)  # Array of message objects
    context = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    message_count = Column(Integer, default=0)
    
    # Relationship
    session = relationship("AgentSessionModel", backref="conversations")
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_conversation_session', 'session_id'),
        Index('idx_conversation_updated', 'updated_at'),
    )

class APIKeyModel(Base):
    """API key management."""
    __tablename__ = "api_keys"
    
    id = Column(Integer, primary_key=True, index=True)
    key_id = Column(String(255), unique=True, nullable=False, index=True)
    key_hash = Column(String(255), nullable=False)  # Hashed API key
    name = Column(String(255), nullable=False)
    description = Column(Text)
    permissions = Column(JSON, default=list)  # List of allowed operations
    rate_limit = Column(Integer, default=1000)  # Requests per hour
    created_by = Column(String(255))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_used = Column(DateTime(timezone=True))
    is_active = Column(Boolean, default=True, index=True)
    expires_at = Column(DateTime(timezone=True))
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_api_key_active', 'key_id', 'is_active'),
        Index('idx_api_key_expires', 'expires_at'),
    )

class RateLimitModel(Base):
    """Rate limiting tracking."""
    __tablename__ = "rate_limits"
    
    id = Column(Integer, primary_key=True, index=True)
    identifier = Column(String(255), nullable=False, index=True)  # API key, user ID, IP
    endpoint = Column(String(255), nullable=False, index=True)
    request_count = Column(Integer, default=0)
    window_start = Column(DateTime(timezone=True), nullable=False)
    window_end = Column(DateTime(timezone=True), nullable=False)
    limit_exceeded = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_rate_limit_identifier_endpoint', 'identifier', 'endpoint'),
        Index('idx_rate_limit_window', 'window_start', 'window_end'),
    )

class NotificationModel(Base):
    """Notification queue."""
    __tablename__ = "notifications"
    
    id = Column(Integer, primary_key=True, index=True)
    recipient_id = Column(String(255), nullable=False, index=True)
    channel_type = Column(String(50), nullable=False, index=True)  # slack, email, webhook
    channel_id = Column(String(255), index=True)
    title = Column(String(500))
    message = Column(Text, nullable=False)
    data = Column(JSON)
    priority = Column(String(20), default='normal', index=True)  # low, normal, high, urgent
    status = Column(String(20), default='pending', index=True)  # pending, sent, failed
    scheduled_for = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    sent_at = Column(DateTime(timezone=True))
    attempts = Column(Integer, default=0)
    error_message = Column(Text)
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_notification_recipient_status', 'recipient_id', 'status'),
        Index('idx_notification_scheduled', 'scheduled_for'),
        Index('idx_notification_priority_status', 'priority', 'status'),
    )

class CacheModel(Base):
    """Simple key-value cache storage."""
    __tablename__ = "cache"
    
    id = Column(Integer, primary_key=True, index=True)
    cache_key = Column(String(255), unique=True, nullable=False, index=True)
    cache_value = Column(JSON, nullable=False)
    expires_at = Column(DateTime(timezone=True), index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    hit_count = Column(Integer, default=0)
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_cache_expires', 'expires_at'),
    )

# Create all tables when this module is imported
# Note: In production, you'd use Alembic migrations instead
def create_all_tables():
    """Create all database tables."""
    from .database import engine
    if engine:
        Base.metadata.create_all(bind=engine)
