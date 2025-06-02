"""
Pydantic schemas for data validation and serialization.
"""
from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, ConfigDict
from enum import Enum

# Enums
class EventType(str, Enum):
    """Event types for logging."""
    NOTION_PAGE_CREATED = "notion_page_created"
    NOTION_PAGE_UPDATED = "notion_page_updated"
    NOTION_DATABASE_UPDATED = "notion_database_updated"
    SLACK_MESSAGE = "slack_message"
    SLACK_APP_MENTION = "slack_app_mention"
    SLACK_COMMAND = "slack_command"
    AGENT_RESPONSE = "agent_response"
    WORKFLOW_EXECUTED = "workflow_executed"
    ERROR_OCCURRED = "error_occurred"

class WorkflowType(str, Enum):
    """Workflow types."""
    SYNC_NOTION_TO_SLACK = "sync_notion_to_slack"
    DAILY_DIGEST = "daily_digest"
    STATUS_UPDATE = "status_update"
    SMART_ROUTING = "smart_routing"
    TASK_CREATION = "task_creation"

class EventStatus(str, Enum):
    """Event processing status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"

# Base schemas
class BaseSchema(BaseModel):
    """Base schema with common configuration."""
    model_config = ConfigDict(from_attributes=True)

# Agent Session schemas
class AgentSessionBase(BaseSchema):
    """Base agent session schema."""
    session_id: str = Field(..., description="Unique session identifier")
    user_id: Optional[str] = Field(None, description="User identifier")
    channel_id: Optional[str] = Field(None, description="Channel identifier")
    context: Dict[str, Any] = Field(default_factory=dict, description="Session context")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

class AgentSessionCreate(AgentSessionBase):
    """Schema for creating agent sessions."""
    pass

class AgentSessionUpdate(BaseSchema):
    """Schema for updating agent sessions."""
    context: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
    last_activity: Optional[datetime] = None

class AgentSession(AgentSessionBase):
    """Full agent session schema."""
    id: int
    created_at: datetime
    updated_at: datetime
    last_activity: datetime
    is_active: bool = True

# Workflow Configuration schemas
class WorkflowConfigBase(BaseSchema):
    """Base workflow configuration schema."""
    name: str = Field(..., description="Workflow name")
    workflow_type: WorkflowType = Field(..., description="Type of workflow")
    source_config: Dict[str, Any] = Field(..., description="Source configuration")
    target_config: Dict[str, Any] = Field(..., description="Target configuration")
    schedule_config: Optional[Dict[str, Any]] = Field(None, description="Schedule configuration")
    filters: Optional[Dict[str, Any]] = Field(None, description="Filter conditions")
    transformations: Optional[List[Dict[str, Any]]] = Field(None, description="Data transformations")
    is_active: bool = Field(True, description="Whether workflow is active")

class WorkflowConfigCreate(WorkflowConfigBase):
    """Schema for creating workflow configurations."""
    pass

class WorkflowConfigUpdate(BaseSchema):
    """Schema for updating workflow configurations."""
    name: Optional[str] = None
    source_config: Optional[Dict[str, Any]] = None
    target_config: Optional[Dict[str, Any]] = None
    schedule_config: Optional[Dict[str, Any]] = None
    filters: Optional[Dict[str, Any]] = None
    transformations: Optional[List[Dict[str, Any]]] = None
    is_active: Optional[bool] = None

class WorkflowConfig(WorkflowConfigBase):
    """Full workflow configuration schema."""
    id: int
    created_at: datetime
    updated_at: datetime
    last_executed: Optional[datetime] = None
    execution_count: int = 0

# Event Log schemas
class EventLogBase(BaseSchema):
    """Base event log schema."""
    event_type: EventType = Field(..., description="Type of event")
    source: str = Field(..., description="Event source (notion, slack, agent)")
    event_data: Dict[str, Any] = Field(..., description="Event data")
    user_id: Optional[str] = Field(None, description="Associated user ID")
    session_id: Optional[str] = Field(None, description="Associated session ID")
    correlation_id: Optional[str] = Field(None, description="Correlation ID for tracking")

class EventLogCreate(EventLogBase):
    """Schema for creating event logs."""
    pass

class EventLog(EventLogBase):
    """Full event log schema."""
    id: int
    timestamp: datetime
    status: EventStatus = EventStatus.COMPLETED
    processing_time_ms: Optional[float] = None
    error_message: Optional[str] = None

# User Mapping schemas
class UserMappingBase(BaseSchema):
    """Base user mapping schema."""
    slack_user_id: str = Field(..., description="Slack user ID")
    notion_user_id: Optional[str] = Field(None, description="Notion user ID")
    email: Optional[str] = Field(None, description="User email")
    display_name: Optional[str] = Field(None, description="Display name")
    preferences: Dict[str, Any] = Field(default_factory=dict, description="User preferences")

class UserMappingCreate(UserMappingBase):
    """Schema for creating user mappings."""
    pass

class UserMappingUpdate(BaseSchema):
    """Schema for updating user mappings."""
    notion_user_id: Optional[str] = None
    email: Optional[str] = None
    display_name: Optional[str] = None
    preferences: Optional[Dict[str, Any]] = None

class UserMapping(UserMappingBase):
    """Full user mapping schema."""
    id: int
    created_at: datetime
    updated_at: datetime
    last_seen: Optional[datetime] = None
    is_active: bool = True

# API Response schemas
class APIResponse(BaseSchema):
    """Standard API response schema."""
    success: bool = Field(..., description="Whether the request was successful")
    message: Optional[str] = Field(None, description="Response message")
    data: Optional[Any] = Field(None, description="Response data")
    error: Optional[str] = Field(None, description="Error message if failed")

class PaginatedResponse(BaseSchema):
    """Paginated response schema."""
    items: List[Any] = Field(..., description="List of items")
    total: int = Field(..., description="Total number of items")
    page: int = Field(..., description="Current page number")
    per_page: int = Field(..., description="Items per page")
    pages: int = Field(..., description="Total number of pages")

# Health Check schemas
class HealthStatus(BaseSchema):
    """Health check status schema."""
    status: str = Field(..., description="Overall health status")
    timestamp: datetime = Field(..., description="Check timestamp")
    components: Dict[str, str] = Field(..., description="Component health status")
    metrics: Optional[Dict[str, Any]] = Field(None, description="System metrics")

# Notion-specific schemas
class NotionPageReference(BaseSchema):
    """Reference to a Notion page."""
    page_id: str = Field(..., description="Notion page ID")
    title: str = Field(..., description="Page title")
    url: Optional[str] = Field(None, description="Page URL")
    database_id: Optional[str] = Field(None, description="Parent database ID")

class NotionDatabaseReference(BaseSchema):
    """Reference to a Notion database."""
    database_id: str = Field(..., description="Notion database ID")
    title: str = Field(..., description="Database title")
    url: Optional[str] = Field(None, description="Database URL")

# Slack-specific schemas
class SlackChannelReference(BaseSchema):
    """Reference to a Slack channel."""
    channel_id: str = Field(..., description="Slack channel ID")
    name: str = Field(..., description="Channel name")
    is_private: bool = Field(False, description="Whether channel is private")
    topic: Optional[str] = Field(None, description="Channel topic")

class SlackUserReference(BaseSchema):
    """Reference to a Slack user."""
    user_id: str = Field(..., description="Slack user ID")
    username: str = Field(..., description="Username")
    display_name: Optional[str] = Field(None, description="Display name")
    email: Optional[str] = Field(None, description="Email address")

# Workflow execution schemas
class WorkflowExecution(BaseSchema):
    """Workflow execution result."""
    workflow_id: int = Field(..., description="Workflow configuration ID")
    execution_id: str = Field(..., description="Unique execution ID")
    status: EventStatus = Field(..., description="Execution status")
    started_at: datetime = Field(..., description="Execution start time")
    completed_at: Optional[datetime] = Field(None, description="Execution completion time")
    duration_ms: Optional[float] = Field(None, description="Execution duration in milliseconds")
    items_processed: int = Field(0, description="Number of items processed")
    errors: List[str] = Field(default_factory=list, description="Execution errors")
    result: Optional[Dict[str, Any]] = Field(None, description="Execution result")

# Agent conversation schemas
class AgentMessage(BaseSchema):
    """Agent conversation message."""
    role: str = Field(..., description="Message role (user, assistant, system)")
    content: str = Field(..., description="Message content")
    timestamp: datetime = Field(..., description="Message timestamp")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Message metadata")

class AgentConversation(BaseSchema):
    """Agent conversation."""
    session_id: str = Field(..., description="Session ID")
    messages: List[AgentMessage] = Field(..., description="Conversation messages")
    context: Dict[str, Any] = Field(default_factory=dict, description="Conversation context")
    created_at: datetime = Field(..., description="Conversation start time")
    updated_at: datetime = Field(..., description="Last update time")
