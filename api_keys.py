"""
Chain Sentinel — API Key System
Simple API key management for premium users
"""

import hashlib
import secrets
import json
import os
from datetime import datetime, timedelta
from typing import Optional
from pathlib import Path

# API key storage (in production, use a database)
API_KEYS_FILE = Path.home() / ".chain-sentinel" / "api_keys.json"

class APIKeyManager:
    def __init__(self):
        self.keys = self._load_keys()
    
    def _load_keys(self) -> dict:
        """Load API keys from file"""
        if API_KEYS_FILE.exists():
            try:
                with open(API_KEYS_FILE, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def _save_keys(self):
        """Save API keys to file"""
        API_KEYS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(API_KEYS_FILE, 'w') as f:
            json.dump(self.keys, f, indent=2)
    
    def generate_key(self, user_id: str, plan: str = "pro") -> str:
        """Generate a new API key for a user"""
        # Generate a random key
        key = f"cs_{secrets.token_urlsafe(32)}"
        
        # Store key info
        self.keys[key] = {
            "user_id": user_id,
            "plan": plan,
            "created_at": datetime.now().isoformat(),
            "is_active": True,
            "usage_count": 0,
            "last_used": None
        }
        
        self._save_keys()
        return key
    
    def validate_key(self, key: str) -> Optional[dict]:
        """Validate an API key and return its info"""
        if key not in self.keys:
            return None
        
        key_info = self.keys[key]
        
        # Check if key is active
        if not key_info.get("is_active", False):
            return None
        
        # Update usage
        key_info["usage_count"] = key_info.get("usage_count", 0) + 1
        key_info["last_used"] = datetime.now().isoformat()
        self._save_keys()
        
        return key_info
    
    def get_usage_limits(self, plan: str) -> dict:
        """Get usage limits for a plan"""
        limits = {
            "free": {
                "scans_per_minute": 20,
                "scans_per_day": 1000,
                "api_calls_per_day": 0,
                "wallet_monitoring": 0,
                "features": ["basic_scan", "honeypot_detection"]
            },
            "pro": {
                "scans_per_minute": 100,
                "scans_per_day": 10000,
                "api_calls_per_day": 1000,
                "wallet_monitoring": 5,
                "features": ["basic_scan", "honeypot_detection", "api_access", "wallet_monitoring", "email_alerts"]
            },
            "enterprise": {
                "scans_per_minute": 1000,
                "scans_per_day": 100000,
                "api_calls_per_day": 10000,
                "wallet_monitoring": 50,
                "features": ["basic_scan", "honeypot_detection", "api_access", "wallet_monitoring", "email_alerts", "custom_integrations", "white_label"]
            }
        }
        return limits.get(plan, limits["free"])
    
    def deactivate_key(self, key: str) -> bool:
        """Deactivate an API key"""
        if key in self.keys:
            self.keys[key]["is_active"] = False
            self._save_keys()
            return True
        return False
    
    def get_user_keys(self, user_id: str) -> list:
        """Get all keys for a user"""
        return [
            {"key": key, **info}
            for key, info in self.keys.items()
            if info.get("user_id") == user_id
        ]

# Global instance
api_key_manager = APIKeyManager()
