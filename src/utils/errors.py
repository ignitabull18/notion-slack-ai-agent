"""
Custom error classes for the Notion-Slack AI Agent.
"""

class AgentError(Exception):
    """Base exception class for agent-related errors."""
    
    def __init__(self, message: str, error_code: str = None, details: dict = None):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)

class NotionError(AgentError):
    """Exception for Notion API related errors."""
    
    def __init__(self, message: str, notion_error_code: str = None, **kwargs):
        self.notion_error_code = notion_error_code
        super().__init__(message, error_code="NOTION_ERROR", **kwargs)

class SlackError(AgentError):
    """Exception for Slack API related errors."""
    
    def __init__(self, message: str, slack_error_code: str = None, **kwargs):
        self.slack_error_code = slack_error_code
        super().__init__(message, error_code="SLACK_ERROR", **kwargs)

class ValidationError(AgentError):
    """Exception for input validation errors."""
    
    def __init__(self, message: str, field: str = None, **kwargs):
        self.field = field
        super().__init__(message, error_code="VALIDATION_ERROR", **kwargs)

class AuthenticationError(AgentError):
    """Exception for authentication and authorization errors."""
    
    def __init__(self, message: str, auth_type: str = None, **kwargs):
        self.auth_type = auth_type
        super().__init__(message, error_code="AUTH_ERROR", **kwargs)

class RateLimitError(AgentError):
    """Exception for rate limiting errors."""
    
    def __init__(self, message: str, service: str = None, retry_after: int = None, **kwargs):
        self.service = service
        self.retry_after = retry_after
        super().__init__(message, error_code="RATE_LIMIT_ERROR", **kwargs)

class WorkflowError(AgentError):
    """Exception for workflow execution errors."""
    
    def __init__(self, message: str, workflow_step: str = None, **kwargs):
        self.workflow_step = workflow_step
        super().__init__(message, error_code="WORKFLOW_ERROR", **kwargs)

class ConfigurationError(AgentError):
    """Exception for configuration related errors."""
    
    def __init__(self, message: str, config_key: str = None, **kwargs):
        self.config_key = config_key
        super().__init__(message, error_code="CONFIG_ERROR", **kwargs)
