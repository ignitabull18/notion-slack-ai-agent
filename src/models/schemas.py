"""
Database schemas and ORM models for the Notion-Slack AI Agent.
"""
from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy import (
    Column, Integer, String, DateTime, Boolean, Text, JSON,
    ForeignKey, UniqueConstraint, Index
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .database import Base

class User(Base):
    """User model for storing user information and preferences."""
    
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    slack_user_id = Column(String(50), unique=True, index=True, nullable=False)
    slack_team_id = Column(String(50), index=True, nullable=False)
    email = Column(String(255), unique=True, index=True)
    display_name = Column(String(255))
    real_name = Column(String(255))
    timezone = Column(String(50))
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_seen_at = Column(DateTime(timezone=True))
    
    # Relationships
    preferences = relationship("UserPreferences", back_populates="user", uselist=False)
    agent_sessions = relationship("AgentSession", back_populates="user")
    workflow_executions = relationship("WorkflowExecution", back_populates="user")
    
    __table_args__ = (
        UniqueConstraint('slack_user_id', 'slack_team_id', name='unique_user_team'),
        Index('idx_user_active', 'is_active'),
    )

class UserPreferences(Base):
    """User preferences and settings."""
    
    __tablename__ = "user_preferences"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    
    # Notification preferences
    notifications_enabled = Column(Boolean, default=True)
    digest_frequency = Column(String(20), default="daily")  # daily, weekly, never
    mention_notifications = Column(Boolean, default=True)
    
    # Integration preferences
    default_notion_database = Column(String(100))
    default_slack_channel = Column(String(50))
    preferred_timezone = Column(String(50))
    
    # Agent behavior preferences
    response_style = Column(String(20), default="detailed")  # brief, detailed, verbose
    auto_create_tasks = Column(Boolean, default=False)
    auto_sync_enabled = Column(Boolean, default=True)
    
    # Custom settings (JSON)
    custom_settings = Column(JSON, default=dict)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="preferences")

class AgentSession(Base):
    """Agent conversation sessions and context."""
    
    __tablename__ = "agent_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(100), unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Session metadata
    channel_id = Column(String(50))  # Slack channel if applicable
    thread_ts = Column(String(50))   # Slack thread timestamp
    context_type = Column(String(20), default="chat")  # chat, webhook, api
    
    # Conversation data
    messages = Column(JSON, default=list)  # List of message objects
    context = Column(JSON, default=dict)   # Session context and memory
    
    # Session state
    is_active = Column(Boolean, default=True)
    last_activity = Column(DateTime(timezone=True), server_default=func.now())
    
    # Performance metrics
    total_messages = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    average_response_time = Column(Integer)  # milliseconds
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="agent_sessions")
    
    __table_args__ = (
        Index('idx_session_active', 'is_active'),
        Index('idx_session_activity', 'last_activity'),
        Index('idx_session_user_channel', 'user_id', 'channel_id'),
    )

class NotionDatabase(Base):
    """Notion database configurations and mappings."""
    
    __tablename__ = "notion_databases"
    
    id = Column(Integer, primary_key=True, index=True)
    database_id = Column(String(100), unique=True, index=True, nullable=False)
    
    # Database metadata
    title = Column(String(255), nullable=False)
    description = Column(Text)
    notion_url = Column(String(500))
    
    # Schema information
    properties_schema = Column(JSON, default=dict)  # Database property definitions
    last_schema_update = Column(DateTime(timezone=True))
    
    # Integration settings
    slack_channel_id = Column(String(50))  # Associated Slack channel
    auto_sync_enabled = Column(Boolean, default=False)
    sync_frequency = Column(String(20), default="manual")  # manual, hourly, daily
    
    # Workflow settings
    workflow_templates = Column(JSON, default=list)  # List of workflow configurations
    notification_rules = Column(JSON, default=list)  # Notification rules
    
    # Access control
    created_by_user_id = Column(Integer, ForeignKey("users.id"))
    is_public = Column(Boolean, default=False)
    allowed_users = Column(JSON, default=list)  # List of user IDs with access
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_sync_at = Column(DateTime(timezone=True))
    
    __table_args__ = (
        Index('idx_database_sync', 'auto_sync_enabled', 'last_sync_at'),
        Index('idx_database_channel', 'slack_channel_id'),
    )

class SlackWorkspace(Base):
    """Slack workspace configurations and settings."""
    
    __tablename__ = "slack_workspaces"
    
    id = Column(Integer, primary_key=True, index=True)
    team_id = Column(String(50), unique=True, index=True, nullable=False)
    
    # Workspace metadata
    team_name = Column(String(255), nullable=False)
    team_domain = Column(String(255))
    team_url = Column(String(500))
    
    # Bot installation info
    bot_user_id = Column(String(50))
    bot_access_token = Column(String(500))  # Encrypted
    app_id = Column(String(50))
    
    # Integration settings
    auto_response_enabled = Column(Boolean, default=True)
    default_notification_channel = Column(String(50))
    allowed_channels = Column(JSON, default=list)  # List of allowed channel IDs
    
    # Feature flags
    slash_commands_enabled = Column(Boolean, default=True)
    webhooks_enabled = Column(Boolean, default=True)
    mentions_enabled = Column(Boolean, default=True)
    
    # Rate limiting
    daily_api_limit = Column(Integer, default=1000)
    current_daily_usage = Column(Integer, default=0)
    last_usage_reset = Column(DateTime(timezone=True), server_default=func.now())
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_active_at = Column(DateTime(timezone=True))
    
    __table_args__ = (
        Index('idx_workspace_active', 'last_active_at'),
        Index('idx_workspace_usage', 'current_daily_usage', 'last_usage_reset'),
    )

class WorkflowExecution(Base):
    """Workflow execution logs and results."""
    
    __tablename__ = "workflow_executions"
    
    id = Column(Integer, primary_key=True, index=True)
    execution_id = Column(String(100), unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Workflow metadata
    workflow_type = Column(String(50), nullable=False)  # sync, digest, task_creation, etc.
    workflow_name = Column(String(255))
    trigger_type = Column(String(50))  # manual, scheduled, webhook, api
    
    # Execution data
    input_data = Column(JSON, default=dict)    # Input parameters
    output_data = Column(JSON, default=dict)   # Execution results
    execution_log = Column(JSON, default=list) # Step-by-step execution log
    
    # Status and timing
    status = Column(String(20), default="pending")  # pending, running, completed, failed
    progress_percentage = Column(Integer, default=0)
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    duration_ms = Column(Integer)  # Execution duration in milliseconds
    
    # Error handling
    error_message = Column(Text)
    error_details = Column(JSON)
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    
    # Performance metrics
    api_calls_made = Column(Integer, default=0)
    data_processed = Column(Integer, default=0)  # Number of records/items processed
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="workflow_executions")
    
    __table_args__ = (
        Index('idx_execution_status', 'status'),
        Index('idx_execution_type', 'workflow_type'),
        Index('idx_execution_user_date', 'user_id', 'created_at'),
    )

class APIKey(Base):
    """API keys for external access to the agent system."""
    
    __tablename__ = "api_keys"
    
    id = Column(Integer, primary_key=True, index=True)
    key_id = Column(String(50), unique=True, index=True, nullable=False)
    key_hash = Column(String(255), nullable=False)  # Hashed API key
    
    # Key metadata
    name = Column(String(255), nullable=False)
    description = Column(Text)
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Permissions and restrictions
    scopes = Column(JSON, default=list)  # List of allowed scopes/permissions
    allowed_ips = Column(JSON, default=list)  # IP whitelist
    rate_limit_per_hour = Column(Integer, default=1000)
    
    # Usage tracking
    last_used_at = Column(DateTime(timezone=True))
    total_requests = Column(Integer, default=0)
    current_hour_requests = Column(Integer, default=0)
    last_hour_reset = Column(DateTime(timezone=True), server_default=func.now())
    
    # Status
    is_active = Column(Boolean, default=True)
    expires_at = Column(DateTime(timezone=True))
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    __table_args__ = (
        Index('idx_key_active', 'is_active'),
        Index('idx_key_usage', 'current_hour_requests', 'last_hour_reset'),
    )

class SystemMetrics(Base):
    """System performance and usage metrics."""
    
    __tablename__ = "system_metrics"
    
    id = Column(Integer, primary_key=True, index=True)
    metric_name = Column(String(100), nullable=False)
    metric_type = Column(String(20), nullable=False)  # counter, gauge, histogram
    
    # Metric data
    value = Column(Integer, nullable=False)
    tags = Column(JSON, default=dict)  # Additional metric tags/labels
    
    # Timestamps
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        Index('idx_metrics_name_time', 'metric_name', 'timestamp'),
        Index('idx_metrics_type', 'metric_type'),
    )
