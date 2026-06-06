"""
Chain Sentinel — Python SDK
Free token safety scanner across 9 blockchains.
"""

from .client import ChainSentinel
from .models import ScanResult, HealthResponse, Plan, WebhookInfo
from .exceptions import (
    ChainSentinelError,
    RateLimitError,
    AuthenticationError,
    NotFoundError,
)

__version__ = "0.4.0"
__all__ = [
    "ChainSentinel",
    "ScanResult",
    "HealthResponse",
    "Plan",
    "WebhookInfo",
    "ChainSentinelError",
    "RateLimitError",
    "AuthenticationError",
    "NotFoundError",
]
