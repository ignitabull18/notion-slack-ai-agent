"""
Rate limiting service for the Notion-Slack AI Agent.
"""
import time
import redis
from typing import Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
import json
import logging

from src.config import get_settings
from src.utils.errors import RateLimitError

logger = logging.getLogger(__name__)
settings = get_settings()

@dataclass
class RateLimit:
    """Rate limit configuration."""
    requests: int
    window_seconds: int
    burst_allowance: int = 0

class RateLimiter:
    """Redis-based rate limiter with sliding window algorithm."""
    
    def __init__(self, redis_url: str = None):
        """Initialize rate limiter with Redis connection."""
        self.redis_client = redis.from_url(redis_url or settings.redis_url)
        
        # Default rate limits
        self.default_limits = {
            "api": RateLimit(1000, 3600),  # 1000 requests per hour
            "webhook": RateLimit(100, 60),  # 100 requests per minute
            "user": RateLimit(60, 60),     # 60 requests per minute per user
            "ip": RateLimit(100, 60),      # 100 requests per minute per IP
            "slack_command": RateLimit(10, 60),  # 10 commands per minute
            "notion_api": RateLimit(1000, 3600), # 1000 Notion API calls per hour
            "slack_api": RateLimit(50, 60),      # 50 Slack API calls per minute
        }
    
    def check_rate_limit(self, 
                        key: str, 
                        limit_type: str = "api",
                        custom_limit: Optional[RateLimit] = None) -> Tuple[bool, Dict[str, Any]]:
        """
        Check if request is within rate limits.
        
        Args:
            key: Unique identifier for the rate limit (e.g., user_id, ip_address)
            limit_type: Type of rate limit to apply
            custom_limit: Custom rate limit configuration
        
        Returns:
            Tuple of (allowed, metadata)
        """
        rate_limit = custom_limit or self.default_limits.get(limit_type, self.default_limits["api"])
        
        redis_key = f"rate_limit:{limit_type}:{key}"
        now = time.time()
        window_start = now - rate_limit.window_seconds
        
        pipe = self.redis_client.pipeline()
        
        try:
            # Remove expired entries
            pipe.zremrangebyscore(redis_key, "-inf", window_start)
            
            # Count current requests in window
            pipe.zcard(redis_key)
            
            # Add current request
            pipe.zadd(redis_key, {str(now): now})
            
            # Set expiration
            pipe.expire(redis_key, rate_limit.window_seconds + 60)
            
            results = pipe.execute()
            current_count = results[1] + 1  # +1 for the request we just added
            
            allowed = current_count <= rate_limit.requests
            
            if not allowed:
                # Remove the request we added since it's not allowed
                self.redis_client.zrem(redis_key, str(now))
            
            # Calculate reset time
            oldest_request = self.redis_client.zrange(redis_key, 0, 0, withscores=True)
            reset_time = None
            if oldest_request:
                reset_time = oldest_request[0][1] + rate_limit.window_seconds
            
            metadata = {
                "limit": rate_limit.requests,
                "remaining": max(0, rate_limit.requests - current_count),
                "reset_time": reset_time,
                "window_seconds": rate_limit.window_seconds,
                "current_count": current_count
            }
            
            return allowed, metadata
            
        except redis.RedisError as e:
            logger.error(f"Redis error in rate limiter: {e}")
            # Fail open - allow request if Redis is unavailable
            return True, {"error": "rate_limiter_unavailable"}
    
    def get_rate_limit_status(self, key: str, limit_type: str = "api") -> Dict[str, Any]:
        """
        Get current rate limit status without incrementing counter.
        
        Args:
            key: Unique identifier for the rate limit
            limit_type: Type of rate limit
        
        Returns:
            Rate limit status dictionary
        """
        rate_limit = self.default_limits.get(limit_type, self.default_limits["api"])
        redis_key = f"rate_limit:{limit_type}:{key}"
        now = time.time()
        window_start = now - rate_limit.window_seconds
        
        try:
            # Clean expired entries
            self.redis_client.zremrangebyscore(redis_key, "-inf", window_start)
            
            # Count current requests
            current_count = self.redis_client.zcard(redis_key)
            
            # Get oldest request time
            oldest_request = self.redis_client.zrange(redis_key, 0, 0, withscores=True)
            reset_time = None
            if oldest_request:
                reset_time = oldest_request[0][1] + rate_limit.window_seconds
            
            return {
                "limit": rate_limit.requests,
                "remaining": max(0, rate_limit.requests - current_count),
                "reset_time": reset_time,
                "window_seconds": rate_limit.window_seconds,
                "current_count": current_count
            }
            
        except redis.RedisError as e:
            logger.error(f"Redis error getting rate limit status: {e}")
            return {"error": "rate_limiter_unavailable"}
    
    def reset_rate_limit(self, key: str, limit_type: str = "api") -> bool:
        """
        Reset rate limit for a key.
        
        Args:
            key: Unique identifier for the rate limit
            limit_type: Type of rate limit
        
        Returns:
            True if reset successfully, False otherwise
        """
        redis_key = f"rate_limit:{limit_type}:{key}"
        
        try:
            self.redis_client.delete(redis_key)
            return True
        except redis.RedisError as e:
            logger.error(f"Redis error resetting rate limit: {e}")
            return False
    
    def set_custom_limit(self, key: str, limit_type: str, rate_limit: RateLimit) -> bool:
        """
        Set custom rate limit for a specific key.
        
        Args:
            key: Unique identifier
            limit_type: Type of rate limit
            rate_limit: Custom rate limit configuration
        
        Returns:
            True if set successfully, False otherwise
        """
        config_key = f"rate_limit_config:{limit_type}:{key}"
        
        try:
            config_data = {
                "requests": rate_limit.requests,
                "window_seconds": rate_limit.window_seconds,
                "burst_allowance": rate_limit.burst_allowance
            }
            self.redis_client.setex(
                config_key, 
                24 * 3600,  # 24 hours expiration
                json.dumps(config_data)
            )
            return True
        except redis.RedisError as e:
            logger.error(f"Redis error setting custom limit: {e}")
            return False
    
    def get_custom_limit(self, key: str, limit_type: str) -> Optional[RateLimit]:
        """
        Get custom rate limit for a key.
        
        Args:
            key: Unique identifier
            limit_type: Type of rate limit
        
        Returns:
            RateLimit object if custom limit exists, None otherwise
        """
        config_key = f"rate_limit_config:{limit_type}:{key}"
        
        try:
            config_data = self.redis_client.get(config_key)
            if config_data:
                config = json.loads(config_data)
                return RateLimit(
                    requests=config["requests"],
                    window_seconds=config["window_seconds"],
                    burst_allowance=config.get("burst_allowance", 0)
                )
        except (redis.RedisError, json.JSONDecodeError) as e:
            logger.error(f"Error getting custom limit: {e}")
        
        return None

class AdaptiveRateLimiter:
    """Advanced rate limiter with adaptive limits based on system load."""
    
    def __init__(self, base_limiter: RateLimiter):
        self.base_limiter = base_limiter
        self.load_history = []
        self.max_history_size = 100
    
    def update_system_load(self, cpu_percent: float, memory_percent: float):
        """Update system load metrics for adaptive limiting."""
        load_score = (cpu_percent + memory_percent) / 2
        self.load_history.append({
            "timestamp": time.time(),
            "load_score": load_score,
            "cpu_percent": cpu_percent,
            "memory_percent": memory_percent
        })
        
        # Keep only recent history
        if len(self.load_history) > self.max_history_size:
            self.load_history = self.load_history[-self.max_history_size:]
    
    def get_adaptive_limit(self, base_limit: RateLimit) -> RateLimit:
        """Calculate adaptive rate limit based on system load."""
        if not self.load_history:
            return base_limit
        
        # Calculate average load over last 10 minutes
        ten_minutes_ago = time.time() - 600
        recent_loads = [
            entry["load_score"] for entry in self.load_history
            if entry["timestamp"] > ten_minutes_ago
        ]
        
        if not recent_loads:
            return base_limit
        
        avg_load = sum(recent_loads) / len(recent_loads)
        
        # Adjust rate limit based on load
        if avg_load > 80:  # High load
            multiplier = 0.5
        elif avg_load > 60:  # Medium load
            multiplier = 0.7
        elif avg_load < 30:  # Low load
            multiplier = 1.5
        else:  # Normal load
            multiplier = 1.0
        
        adapted_requests = int(base_limit.requests * multiplier)
        
        return RateLimit(
            requests=max(1, adapted_requests),  # Ensure at least 1 request
            window_seconds=base_limit.window_seconds,
            burst_allowance=base_limit.burst_allowance
        )
    
    def check_adaptive_rate_limit(self, key: str, limit_type: str = "api") -> Tuple[bool, Dict[str, Any]]:
        """Check rate limit with adaptive adjustment."""
        base_limit = self.base_limiter.default_limits.get(limit_type)
        if not base_limit:
            return self.base_limiter.check_rate_limit(key, limit_type)
        
        adaptive_limit = self.get_adaptive_limit(base_limit)
        return self.base_limiter.check_rate_limit(key, limit_type, adaptive_limit)

class RateLimitMiddleware:
    """FastAPI middleware for rate limiting."""
    
    def __init__(self, rate_limiter: RateLimiter):
        self.rate_limiter = rate_limiter
    
    async def __call__(self, request, call_next):
        """Process request with rate limiting."""
        # Extract identifier (IP, user ID, API key, etc.)
        client_ip = request.client.host
        user_id = getattr(request.state, "user_id", None)
        api_key = getattr(request.state, "api_key_id", None)
        
        # Determine rate limit key and type
        if api_key:
            limit_key = f"api_key:{api_key}"
            limit_type = "api"
        elif user_id:
            limit_key = f"user:{user_id}"
            limit_type = "user"
        else:
            limit_key = f"ip:{client_ip}"
            limit_type = "ip"
        
        # Check rate limit
        allowed, metadata = self.rate_limiter.check_rate_limit(limit_key, limit_type)
        
        if not allowed:
            raise RateLimitError(
                message=f"Rate limit exceeded. Try again in {metadata.get('reset_time', 0) - time.time():.1f} seconds",
                retry_after=int(metadata.get("reset_time", 0) - time.time())
            )
        
        # Add rate limit headers to response
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(metadata.get("limit", 0))
        response.headers["X-RateLimit-Remaining"] = str(metadata.get("remaining", 0))
        if metadata.get("reset_time"):
            response.headers["X-RateLimit-Reset"] = str(int(metadata["reset_time"]))
        
        return response

def require_rate_limit(limit_type: str = "api", custom_limit: Optional[RateLimit] = None):
    """
    Decorator to apply rate limiting to functions.
    
    Args:
        limit_type: Type of rate limit to apply
        custom_limit: Custom rate limit configuration
    """
    def decorator(func):
        async def async_wrapper(*args, **kwargs):
            # This would need to be integrated with FastAPI dependencies
            # For now, it's a placeholder
            return await func(*args, **kwargs)
        
        def sync_wrapper(*args, **kwargs):
            # This would need to be integrated with request context
            # For now, it's a placeholder
            return func(*args, **kwargs)
        
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator

# Global rate limiter instance
rate_limiter = None

def get_rate_limiter() -> RateLimiter:
    """Get global rate limiter instance."""
    global rate_limiter
    if rate_limiter is None:
        rate_limiter = RateLimiter()
    return rate_limiter

def init_rate_limiter(redis_url: str = None) -> RateLimiter:
    """Initialize global rate limiter."""
    global rate_limiter
    rate_limiter = RateLimiter(redis_url)
    return rate_limiter
