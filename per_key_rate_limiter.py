"""
Per-Key Rate Limiter for Chain Sentinel
Tracks rate limits per API key instead of per IP
"""

import time
from collections import defaultdict
from typing import Optional, Dict, Any


class PerKeyRateLimiter:
    """Rate limiter that tracks requests per API key."""
    
    def __init__(self):
        # Store: {api_key: [timestamp1, timestamp2, ...]}
        self.requests: Dict[str, list] = defaultdict(list)
        # Store: {ip_address: [timestamp1, timestamp2, ...]} for unauthenticated requests
        self.ip_requests: Dict[str, list] = defaultdict(list)
    
    def _cleanup_old_requests(self, key: str, window_seconds: int = 60) -> list:
        """Remove requests older than the window."""
        now = time.time()
        if key.startswith("cs_"):
            # API key
            self.requests[key] = [
                t for t in self.requests[key]
                if now - t < window_seconds
            ]
            return self.requests[key]
        else:
            # IP address
            self.ip_requests[key] = [
                t for t in self.ip_requests[key]
                if now - t < window_seconds
            ]
            return self.ip_requests[key]
    
    def is_allowed(
        self,
        identifier: str,
        max_requests: int = 20,
        window_seconds: int = 60
    ) -> bool:
        """
        Check if a request is allowed for the given identifier.
        
        Args:
            identifier: API key (starts with "cs_") or IP address
            max_requests: Maximum requests allowed in the window
            window_seconds: Time window in seconds (default: 60)
        
        Returns:
            True if request is allowed, False if rate limited
        """
        requests = self._cleanup_old_requests(identifier, window_seconds)
        
        if len(requests) >= max_requests:
            return False
        
        # Record this request
        if identifier.startswith("cs_"):
            self.requests[identifier].append(time.time())
        else:
            self.ip_requests[identifier].append(time.time())
        
        return True
    
    def get_remaining(
        self,
        identifier: str,
        max_requests: int = 20,
        window_seconds: int = 60
    ) -> int:
        """Get remaining requests for the identifier."""
        requests = self._cleanup_old_requests(identifier, window_seconds)
        return max(0, max_requests - len(requests))
    
    def get_reset_time(
        self,
        identifier: str,
        window_seconds: int = 60
    ) -> int:
        """Get seconds until the rate limit resets."""
        if identifier.startswith("cs_"):
            requests = self.requests.get(identifier, [])
        else:
            requests = self.ip_requests.get(identifier, [])
        
        if not requests:
            return 0
        
        oldest = min(requests)
        return max(0, int(window_seconds - (time.time() - oldest)))
    
    def get_usage_stats(self, identifier: str) -> Dict[str, Any]:
        """Get usage statistics for an identifier."""
        if identifier.startswith("cs_"):
            requests = self.requests.get(identifier, [])
        else:
            requests = self.ip_requests.get(identifier, [])
        
        now = time.time()
        recent_requests = [t for t in requests if now - t < 60]
        
        return {
            "identifier": identifier,
            "requests_last_minute": len(recent_requests),
            "total_requests": len(requests),
            "oldest_request": min(requests) if requests else None,
            "newest_request": max(requests) if requests else None,
        }
    
    def reset(self, identifier: str) -> None:
        """Reset rate limit for an identifier."""
        if identifier.startswith("cs_"):
            self.requests.pop(identifier, None)
        else:
            self.ip_requests.pop(identifier, None)


# Global rate limiter instance
per_key_rate_limiter = PerKeyRateLimiter()
