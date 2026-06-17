"""
Chain Sentinel — Data Models
"""

from dataclasses import dataclass, field
from typing import Optional, List


@dataclass
class ScanResult:
    """Token safety scan result."""

    address: str
    chain: str
    name: str
    symbol: str

    safety_score: int
    risk_level: str  # "safe", "caution", "danger", "critical"

    is_honeypot: Optional[bool] = None
    can_sell: Optional[bool] = None
    buy_tax: float = 0.0
    sell_tax: float = 0.0

    owner_renounced: Optional[bool] = None
    owner_address: str = ""

    is_verified: Optional[bool] = None
    is_proxy: Optional[bool] = None

    liquidity_locked: Optional[bool] = None
    lock_platform: str = ""

    price_usd: float = 0.0
    volume_24h: float = 0.0
    market_cap: float = 0.0
    holders: int = 0

    data_sources: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    positives: List[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> "ScanResult":
        """Create ScanResult from API response dict."""
        return cls(
            address=data.get("address", ""),
            chain=data.get("chain", ""),
            name=data.get("name", ""),
            symbol=data.get("symbol", ""),
            safety_score=data.get("safety_score", 0),
            risk_level=data.get("risk_level", "unknown"),
            is_honeypot=data.get("is_honeypot"),
            can_sell=data.get("can_sell"),
            buy_tax=data.get("buy_tax", 0.0),
            sell_tax=data.get("sell_tax", 0.0),
            owner_renounced=data.get("owner_renounced"),
            owner_address=data.get("owner_address", ""),
            is_verified=data.get("is_verified"),
            is_proxy=data.get("is_proxy"),
            liquidity_locked=data.get("liquidity_locked"),
            lock_platform=data.get("lock_platform", ""),
            price_usd=data.get("price_usd", 0.0),
            volume_24h=data.get("volume_24h", 0.0),
            market_cap=data.get("market_cap", 0.0),
            holders=data.get("holders", 0),
            data_sources=data.get("data_sources", []),
            warnings=data.get("warnings", []),
            positives=data.get("positives", []),
        )

    @property
    def is_safe(self) -> bool:
        """Quick check: is this token safe (score >= 60, not honeypot)?"""
        return self.safety_score >= 60 and not self.is_honeypot

    @property
    def summary(self) -> str:
        """Human-readable summary."""
        emoji = {"safe": "✅", "caution": "⚠️", "danger": "🔴", "critical": "🚨"}.get(
            self.risk_level, "❓"
        )
        return (
            f"{emoji} {self.name} ({self.symbol}) — Score: {self.safety_score}/100 "
            f"[{self.risk_level.upper()}]"
        )


@dataclass
class HealthResponse:
    """API health check response."""

    status: str
    service: str
    version: str

    @classmethod
    def from_dict(cls, data: dict) -> "HealthResponse":
        return cls(
            status=data.get("status", ""),
            service=data.get("service", ""),
            version=data.get("version", ""),
        )


@dataclass
class Plan:
    """API pricing plan."""

    name: str
    price: float
    currency: str
    interval: str
    features: List[str] = field(default_factory=list)
    limits: dict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict) -> "Plan":
        return cls(
            name=data.get("name", ""),
            price=data.get("price", 0),
            currency=data.get("currency", "USD"),
            interval=data.get("interval", ""),
            features=data.get("features", []),
            limits=data.get("limits", {}),
        )


@dataclass
class WebhookInfo:
    """Webhook subscription info."""

    id: str
    url: str
    events: List[str]
    active: bool
    description: str = ""
    created_at: str = ""
    delivery_count: int = 0
    last_delivery: Optional[str] = None
    secret: Optional[str] = None  # Only returned on creation

    @classmethod
    def from_dict(cls, data: dict) -> "WebhookInfo":
        return cls(
            id=data.get("id", ""),
            url=data.get("url", ""),
            events=data.get("events", []),
            active=data.get("active", True),
            description=data.get("description", ""),
            created_at=data.get("created_at", ""),
            delivery_count=data.get("delivery_count", 0),
            last_delivery=data.get("last_delivery"),
            secret=data.get("secret"),
        )
