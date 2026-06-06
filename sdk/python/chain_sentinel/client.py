"""
Chain Sentinel — API Client
"""

from typing import Optional, List, Dict, Any
import httpx

from .models import ScanResult, HealthResponse, Plan, WebhookInfo
from .exceptions import (
    ChainSentinelError,
    RateLimitError,
    AuthenticationError,
    NotFoundError,
    ValidationError,
)

DEFAULT_BASE_URL = "https://chainshieldsentinel.tech"
DEFAULT_TIMEOUT = 30.0

# Supported chain identifiers
CHAINS = [
    "bsc",
    "eth",
    "base",
    "arbitrum",
    "polygon",
    "avalanche",
    "fantom",
    "optimism",
    "solana",
]

# Valid webhook events
WEBHOOK_EVENTS = ["scan.complete", "scan.risk_high", "scan.honeypot", "key.expired"]


class ChainSentinel:
    """
    Chain Sentinel API client.

    Usage:
        from chain_sentinel import ChainSentinel

        client = ChainSentinel(api_key="cs_your_key")
        result = client.scan("0x0E09FaBB73Bd3Ade0a17ECC321fD13a19e81cE82", chain="bsc")
        print(result.summary)
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._client = httpx.Client(
            base_url=self.base_url,
            timeout=timeout,
            headers=self._build_headers(),
        )

    def _build_headers(self) -> Dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "User-Agent": f"chain-sentinel-python/0.4.0",
        }
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        return headers

    def _handle_response(self, response: httpx.Response) -> dict:
        """Handle API response, raising appropriate exceptions for errors."""
        if response.status_code == 200:
            return response.json()

        try:
            body = response.json()
            detail = body.get("detail", response.text)
        except Exception:
            detail = response.text

        if response.status_code == 400:
            raise ValidationError(detail, response_body=body if "body" in dir() else None)
        elif response.status_code == 401:
            raise AuthenticationError(detail)
        elif response.status_code == 404:
            raise NotFoundError(detail)
        elif response.status_code == 429:
            retry_after = response.headers.get("Retry-After")
            raise RateLimitError(
                detail,
                retry_after=int(retry_after) if retry_after else None,
            )
        else:
            raise ChainSentinelError(
                detail, status_code=response.status_code
            )

    # === Core Scanning ===

    def scan(self, address: str, chain: str = "bsc") -> ScanResult:
        """
        Scan a token for safety indicators.

        Args:
            address: Token contract address.
            chain: Blockchain network (default: "bsc"). Options: bsc, eth, base,
                   arbitrum, polygon, avalanche, fantom, optimism, solana.

        Returns:
            ScanResult with safety score, risk level, and detailed analysis.

        Raises:
            ValidationError: Invalid address or chain.
            RateLimitError: Rate limit exceeded.

        Example:
            result = client.scan("0x0E09FaBB73Bd3Ade0a17ECC321fD13a19e81cE82")
            if result.is_safe:
                print(f"Safe to trade! Score: {result.safety_score}")
        """
        if chain not in CHAINS:
            raise ValidationError(
                f"Invalid chain '{chain}'. Supported: {', '.join(CHAINS)}"
            )

        response = self._client.post(
            "/api/scan",
            json={"address": address, "chain": chain},
        )
        data = self._handle_response(response)
        return ScanResult.from_dict(data)

    # === Health ===

    def health(self) -> HealthResponse:
        """
        Check API health status.

        Returns:
            HealthResponse with status, service name, and version.
        """
        response = self._client.get("/api/health")
        data = self._handle_response(response)
        return HealthResponse.from_dict(data)

    # === API Key Management ===

    def validate_key(self) -> Dict[str, Any]:
        """
        Validate the current API key.

        Returns:
            Dict with valid, plan, usage_count, and limits.

        Raises:
            AuthenticationError: If API key is invalid.
        """
        response = self._client.get("/api/keys/validate")
        return self._handle_response(response)

    def get_plans(self) -> List[Plan]:
        """
        Get available pricing plans.

        Returns:
            List of Plan objects.
        """
        response = self._client.get("/api/plans")
        data = self._handle_response(response)
        return [Plan.from_dict(p) for p in data.get("plans", [])]

    # === Webhooks ===

    def create_webhook(
        self,
        url: str,
        events: Optional[List[str]] = None,
        description: str = "",
    ) -> WebhookInfo:
        """
        Create a webhook subscription. Requires Pro or Enterprise plan.

        Args:
            url: HTTPS endpoint to receive webhook payloads.
            events: List of events to subscribe to. Default: ["scan.complete"].
                    Options: scan.complete, scan.risk_high, scan.honeypot, key.expired.
            description: Optional description for this webhook.

        Returns:
            WebhookInfo with id, secret, and configuration.

        Raises:
            AuthenticationError: If API key is missing or invalid.
            ValidationError: If URL is not HTTPS or events are invalid.

        Example:
            webhook = client.create_webhook(
                url="https://myapp.com/webhooks/chain-sentinel",
                events=["scan.complete", "scan.honeypot"],
                description="Production alerts"
            )
            print(f"Webhook ID: {webhook.id}")
            print(f"Secret: {webhook.secret}")  # Save this!
        """
        if not url.startswith("https://"):
            raise ValidationError("Webhook URL must use HTTPS")

        if events is None:
            events = ["scan.complete"]

        invalid_events = [e for e in events if e not in WEBHOOK_EVENTS]
        if invalid_events:
            raise ValidationError(
                f"Invalid events: {invalid_events}. Valid: {WEBHOOK_EVENTS}"
            )

        response = self._client.post(
            "/api/webhooks",
            json={"url": url, "events": events, "description": description},
        )
        data = self._handle_response(response)
        return WebhookInfo.from_dict(data)

    def list_webhooks(self) -> List[WebhookInfo]:
        """
        List your webhook subscriptions.

        Returns:
            List of WebhookInfo objects.
        """
        response = self._client.get("/api/webhooks")
        data = self._handle_response(response)
        return [WebhookInfo.from_dict(w) for w in data.get("webhooks", [])]

    def delete_webhook(self, webhook_id: str) -> None:
        """
        Delete a webhook subscription.

        Args:
            webhook_id: The webhook ID (e.g., "wh_abc123").

        Raises:
            NotFoundError: If webhook not found.
        """
        response = self._client.delete(f"/api/webhooks/{webhook_id}")
        self._handle_response(response)

    def test_webhook(self, webhook_id: str) -> Dict[str, Any]:
        """
        Send a test payload to a webhook.

        Args:
            webhook_id: The webhook ID to test.

        Returns:
            Dict with delivery status and signature info.

        Raises:
            NotFoundError: If webhook not found.
        """
        response = self._client.post(f"/api/webhooks/{webhook_id}/test")
        return self._handle_response(response)

    # === Context Manager ===

    def close(self) -> None:
        """Close the underlying HTTP client."""
        self._client.close()

    def __enter__(self) -> "ChainSentinel":
        return self

    def __exit__(self, *args) -> None:
        self.close()

    def __repr__(self) -> str:
        key_preview = f"{self.api_key[:8]}..." if self.api_key else "None"
        return f"ChainSentinel(api_key={key_preview}, base_url={self.base_url})"
