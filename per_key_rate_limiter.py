"""
Chain Sentinel — Per-Key Rate Limiter
Replaces IP-based rate limiting with per-API-key tracking
"""

import time
import json
import os
from collections import defaultdict
from typing import Optional, Dict, Any
from pathlib import Path

# Rate limit storage
RATE_LIMIT_FILE = Path.home() / ".chain-sentinel" / "rate_limits.json"


class PerKeyRateLimiter:
    """
    Per-API-key rate limiter with sliding window.
    
    Features:
    - Track requests per API key (not per IP)
    - Sliding window algorithm
    - Proper X-RateLimit-* headers
    - Plan-based limits (free/pro/enterprise)
    - Persistent storage (survives restarts)
    """
    
    def __init__(self):
        self.requests: Dict[str, list] = defaultdict(list)
        self._load_state()
    
    def _load_state(self):
        """Load rate limit state from file"""
        if RATE_LIMIT_FILE.exists():
            try:
                with open(RATE_LIMIT_FILE, 'r') as f:
                    data = json.load(f)
                    # Convert stored timestamps back to lists
                    for key, timestamps in data.items():
                        self.requests[key] = timestamps
            except:
                self.requests = defaultdict(list)
    
    def _save_state(self):
        """Save rate limit state to file"""
        RATE_LIMIT_FILE.parent.mkdir(parents=True, exist_ok=True)
        # Only save keys with recent requests (last 5 minutes)
        cutoff = time.time() - 300
        save_data = {
            key: [t for t in timestamps if t > cutoff]
            for key, timestamps in self.requests.items()
            if timestamps and max(timestamps) > cutoff
        }
        with open(RATE_LIMIT_FILE, 'w') as f:
            json.dump(save_data, f)
    
    def _get_key_id(self, api_key: Optional[str], client_ip: str) -> str:
        """Get unique identifier for rate limiting"""
        if api_key:
            return f"key:{api_key}"
        return f"ip:{client_ip}"
    
    def _get_limits(self, plan: str) -> Dict[str, int]:
        """Get rate limits based on plan"""
        limits = {
            "free": {
                "requests_per_minute": 5,
                "requests_per_hour": 15,
                "requests_per_day": 50,
                "burst": 2  # max concurrent
            },
            "pro": {
                "requests_per_minute": 100,
                "requests_per_hour": 3000,
                "requests_per_day": 30000,
                "burst": 20
            },
            "enterprise": {
                "requests_per_minute": 1000,
                "requests_per_hour": 50000,
                "requests_per_day": 500000,
                "burst": 100
            }
        }
        return limits.get(plan, limits["free"])
    
    def is_allowed(
        self, 
        api_key: Optional[str] = None, 
        client_ip: str = "unknown",
        plan: str = "free"
    ) -> bool:
        """
        Check if request is allowed.
        
        Returns True if request is within limits, False if rate limited.
        """
        key_id = self._get_key_id(api_key, client_ip)
        now = time.time()
        limits = self._get_limits(plan)
        
        # Clean old requests
        self.requests[key_id] = [
            t for t in self.requests[key_id] 
            if now - t < 86400  # Keep 24 hours of history
        ]
        
        # Check per-minute limit
        recent_minute = [
            t for t in self.requests[key_id] 
            if now - t < 60
        ]
        if len(recent_minute) >= limits["requests_per_minute"]:
            return False
        
        # Check per-hour limit
        recent_hour = [
            t for t in self.requests[key_id] 
            if now - t < 3600
        ]
        if len(recent_hour) >= limits["requests_per_hour"]:
            return False
        
        # Check per-day limit
        if len(self.requests[key_id]) >= limits["requests_per_day"]:
            return False
        
        # Request allowed - record it
        self.requests[key_id].append(now)
        
        # Save state periodically (every 10 requests)
        if len(self.requests[key_id]) % 10 == 0:
            self._save_state()
        
        return True
    
    def get_usage(
        self,
        api_key: Optional[str] = None,
        client_ip: str = "unknown",
        plan: str = "free"
    ) -> Dict[str, Any]:
        """
        Get current usage stats for a key/IP.
        
        Returns dict with usage info and remaining limits.
        """
        key_id = self._get_key_id(api_key, client_ip)
        now = time.time()
        limits = self._get_limits(plan)
        
        # Count requests in each window
        recent_minute = len([
            t for t in self.requests.get(key_id, []) 
            if now - t < 60
        ])
        recent_hour = len([
            t for t in self.requests.get(key_id, []) 
            if now - t < 3600
        ])
        recent_day = len(self.requests.get(key_id, []))
        
        # Calculate remaining
        remaining_minute = max(0, limits["requests_per_minute"] - recent_minute)
        remaining_hour = max(0, limits["requests_per_hour"] - recent_hour)
        remaining_day = max(0, limits["requests_per_day"] - recent_day)
        
        # Calculate reset times
        if self.requests.get(key_id):
            minute_oldest = min(
                t for t in self.requests[key_id] 
                if now - t < 60
            ) if recent_minute > 0 else now
            reset_minute = int(60 - (now - minute_oldest))
        else:
            reset_minute = 0
        
        return {
            "limit_minute": limits["requests_per_minute"],
            "limit_hour": limits["requests_per_hour"],
            "limit_day": limits["requests_per_day"],
            "used_minute": recent_minute,
            "used_hour": recent_hour,
            "used_day": recent_day,
            "remaining_minute": remaining_minute,
            "remaining_hour": remaining_hour,
            "remaining_day": remaining_day,
            "reset_minute": max(0, reset_minute),
            "plan": plan
        }
    
    def get_headers(
        self,
        api_key: Optional[str] = None,
        client_ip: str = "unknown",
        plan: str = "free"
    ) -> Dict[str, str]:
        """
        Get X-RateLimit-* headers for HTTP response.
        """
        usage = self.get_usage(api_key, client_ip, plan)
        
        return {
            "X-RateLimit-Limit": str(usage["limit_minute"]),
            "X-RateLimit-Remaining": str(usage["remaining_minute"]),
            "X-RateLimit-Reset": str(int(time.time()) + usage["reset_minute"]),
            "X-RateLimit-Policy": f"{usage['limit_minute']};w=60",
            "X-RateLimit-Limit-Hour": str(usage["limit_hour"]),
            "X-RateLimit-Remaining-Hour": str(usage["remaining_hour"]),
            "X-RateLimit-Limit-Day": str(usage["limit_day"]),
            "X-RateLimit-Remaining-Day": str(usage["remaining_day"])
        }
    
    def cleanup(self):
        """Clean up old rate limit data"""
        cutoff = time.time() - 86400  # 24 hours
        keys_to_remove = []
        
        for key, timestamps in self.requests.items():
            self.requests[key] = [t for t in timestamps if t > cutoff]
            if not self.requests[key]:
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            del self.requests[key]
        
        self._save_state()


# Global instance
per_key_limiter = PerKeyRateLimiter()
