"""
Helper functions and utilities for the Notion-Slack AI Agent.
"""
import re
import time
import asyncio
import functools
from typing import List, Optional, Callable, Any, Dict
from datetime import datetime, timezone
from urllib.parse import urlparse
import html

from .errors import ValidationError, RateLimitError

def sanitize_input(text: str, max_length: int = 2000, allow_html: bool = False) -> str:
    """
    Sanitize user input to prevent injection attacks and ensure safe processing.
    
    Args:
        text: Input text to sanitize
        max_length: Maximum allowed length
        allow_html: Whether to allow HTML tags
    
    Returns:
        Sanitized text string
    
    Raises:
        ValidationError: If input is invalid
    """
    if not isinstance(text, str):
        raise ValidationError("Input must be a string")
    
    # Limit length
    if len(text) > max_length:
        text = text[:max_length]
    
    # Remove or escape HTML if not allowed
    if not allow_html:
        text = html.escape(text)
    
    # Remove potentially dangerous characters
    text = re.sub(r'[<>"\']', '', text)
    
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text

def validate_notion_id(notion_id: str) -> bool:
    """
    Validate a Notion page or database ID.
    
    Args:
        notion_id: The ID to validate
    
    Returns:
        True if valid, False otherwise
    """
    if not isinstance(notion_id, str):
        return False
    
    # Remove hyphens for validation
    clean_id = notion_id.replace('-', '')
    
    # Notion IDs are 32 character hex strings
    return len(clean_id) == 32 and all(c in '0123456789abcdefABCDEF' for c in clean_id)

def validate_slack_channel(channel: str) -> bool:
    """
    Validate a Slack channel ID or name.
    
    Args:
        channel: Channel ID (C1234567890) or name (#general)
    
    Returns:
        True if valid, False otherwise
    """
    if not isinstance(channel, str):
        return False
    
    # Channel ID format: C + 10 characters
    if channel.startswith('C') and len(channel) == 11:
        return channel[1:].isalnum()
    
    # Channel name format: starts with # and contains valid characters
    if channel.startswith('#'):
        name = channel[1:]
        return len(name) > 0 and re.match(r'^[a-z0-9_-]+$', name)
    
    # Allow raw channel names without #
    return len(channel) > 0 and re.match(r'^[a-z0-9_-]+$', channel)

def format_timestamp(timestamp: str, format_type: str = "relative") -> str:
    """
    Format a timestamp for display.
    
    Args:
        timestamp: ISO timestamp string
        format_type: "relative", "absolute", or "slack"
    
    Returns:
        Formatted timestamp string
    """
    try:
        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        now = datetime.now(timezone.utc)
        
        if format_type == "relative":
            diff = now - dt
            
            if diff.days > 0:
                return f"{diff.days} day{'s' if diff.days != 1 else ''} ago"
            elif diff.seconds > 3600:
                hours = diff.seconds // 3600
                return f"{hours} hour{'s' if hours != 1 else ''} ago"
            elif diff.seconds > 60:
                minutes = diff.seconds // 60
                return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
            else:
                return "Just now"
        
        elif format_type == "absolute":
            return dt.strftime("%Y-%m-%d %H:%M:%S UTC")
        
        elif format_type == "slack":
            # Slack timestamp format
            return f"<!date^{int(dt.timestamp())}^{{date_short_pretty}} {{time}}|{dt.isoformat()}>"
        
        else:
            return timestamp
            
    except (ValueError, AttributeError):
        return timestamp

def extract_mentions(text: str) -> Dict[str, List[str]]:
    """
    Extract mentions from text (users, channels, etc.).
    
    Args:
        text: Text to analyze
    
    Returns:
        Dictionary with lists of mentioned users, channels, etc.
    """
    mentions = {
        "users": [],
        "channels": [],
        "urls": [],
        "emails": []
    }
    
    # Extract user mentions: @username or <@U1234567890>
    user_mentions = re.findall(r'<@([UW][A-Z0-9]+)>', text)
    mentions["users"].extend(user_mentions)
    
    # Extract channel mentions: #channel or <#C1234567890>
    channel_mentions = re.findall(r'<#([C][A-Z0-9]+)', text)
    mentions["channels"].extend(channel_mentions)
    
    # Extract URLs
    url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
    urls = re.findall(url_pattern, text)
    mentions["urls"].extend(urls)
    
    # Extract email addresses
    email_pattern = r'\\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Z|a-z]{2,}\\b'
    emails = re.findall(email_pattern, text)
    mentions["emails"].extend(emails)
    
    return mentions

def rate_limit(calls_per_minute: int = 60):
    """
    Decorator to rate limit function calls.
    
    Args:
        calls_per_minute: Maximum calls allowed per minute
    
    Returns:
        Decorated function
    """
    def decorator(func):
        calls = []
        
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            now = time.time()
            
            # Remove calls older than 1 minute
            calls[:] = [call_time for call_time in calls if now - call_time < 60]
            
            # Check if we've exceeded the rate limit
            if len(calls) >= calls_per_minute:
                wait_time = 60 - (now - calls[0])
                raise RateLimitError(
                    f"Rate limit exceeded. Try again in {wait_time:.1f} seconds",
                    service=func.__name__,
                    retry_after=int(wait_time)
                )
            
            # Record this call
            calls.append(now)
            
            return await func(*args, **kwargs)
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            now = time.time()
            
            # Remove calls older than 1 minute
            calls[:] = [call_time for call_time in calls if now - call_time < 60]
            
            # Check if we've exceeded the rate limit
            if len(calls) >= calls_per_minute:
                wait_time = 60 - (now - calls[0])
                raise RateLimitError(
                    f"Rate limit exceeded. Try again in {wait_time:.1f} seconds",
                    service=func.__name__,
                    retry_after=int(wait_time)
                )
            
            # Record this call
            calls.append(now)
            
            return func(*args, **kwargs)
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator

def retry_with_backoff(max_retries: int = 3, base_delay: float = 1.0, max_delay: float = 60.0):
    """
    Decorator to retry function calls with exponential backoff.
    
    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay between retries in seconds
        max_delay: Maximum delay between retries in seconds
    
    Returns:
        Decorated function
    """
    def decorator(func):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    
                    if attempt == max_retries:
                        # Final attempt failed, raise the exception
                        raise e
                    
                    # Calculate delay with exponential backoff
                    delay = min(base_delay * (2 ** attempt), max_delay)
                    await asyncio.sleep(delay)
            
            raise last_exception
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    
                    if attempt == max_retries:
                        # Final attempt failed, raise the exception
                        raise e
                    
                    # Calculate delay with exponential backoff
                    delay = min(base_delay * (2 ** attempt), max_delay)
                    time.sleep(delay)
            
            raise last_exception
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator

def parse_slack_timestamp(ts: str) -> datetime:
    """
    Parse Slack timestamp format to datetime.
    
    Args:
        ts: Slack timestamp (e.g., "1234567890.123456")
    
    Returns:
        datetime object
    """
    try:
        # Slack timestamps are Unix timestamps with microseconds
        timestamp = float(ts)
        return datetime.fromtimestamp(timestamp, tz=timezone.utc)
    except (ValueError, TypeError):
        return datetime.now(timezone.utc)

def chunk_list(items: List[Any], chunk_size: int) -> List[List[Any]]:
    """
    Split a list into chunks of specified size.
    
    Args:
        items: List to chunk
        chunk_size: Maximum size of each chunk
    
    Returns:
        List of chunks
    """
    return [items[i:i + chunk_size] for i in range(0, len(items), chunk_size)]

def safe_get(dictionary: Dict, *keys, default=None):
    """
    Safely get nested dictionary values.
    
    Args:
        dictionary: Dictionary to traverse
        *keys: Sequence of keys to follow
        default: Default value if key path doesn't exist
    
    Returns:
        Value at key path or default
    """
    for key in keys:
        if isinstance(dictionary, dict) and key in dictionary:
            dictionary = dictionary[key]
        else:
            return default
    return dictionary

def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    Truncate text to specified length, adding suffix if truncated.
    
    Args:
        text: Text to truncate
        max_length: Maximum length including suffix
        suffix: Suffix to add if truncated
    
    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return text
    
    truncate_length = max_length - len(suffix)
    return text[:truncate_length] + suffix

def is_valid_url(url: str) -> bool:
    """
    Check if a string is a valid URL.
    
    Args:
        url: URL string to validate
    
    Returns:
        True if valid URL, False otherwise
    """
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except Exception:
        return False

def mask_sensitive_data(text: str) -> str:
    """
    Mask sensitive data in text for logging.
    
    Args:
        text: Text that may contain sensitive data
    
    Returns:
        Text with sensitive data masked
    """
    # Mask email addresses
    text = re.sub(r'\\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Z|a-z]{2,}\\b', '[EMAIL]', text)
    
    # Mask potential API keys/tokens
    text = re.sub(r'\\b[a-zA-Z0-9]{20,}\\b', '[TOKEN]', text)
    
    # Mask phone numbers
    text = re.sub(r'\\b\\d{3}-\\d{3}-\\d{4}\\b', '[PHONE]', text)
    
    return text
