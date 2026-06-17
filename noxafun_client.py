"""
NOXA Fun Launchpad Integration for Chain Sentinel
Scrapes token data from NOXA Fun (fun.noxa.fi) launchpad
"""

import httpx
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime


NOXA_FUN_BASE_URL = "https://awk00kk00gskkw0o8kc488kg.notoriouslywrong.com"
NOXA_DEX_URL = "https://dex.noxa.fi"

# Supported chains on NOXA Fun
NOXA_CHAINS = {
    "robinhood": "robinhood",
    "plasma": "plasma",
    "monad": "monad",
}


@dataclass
class NoxaToken:
    """Token data from NOXA Fun launchpad."""
    
    # Basic info
    address: str
    chain: str
    name: str = ""
    symbol: str = ""
    description: str = ""
    
    # Market data
    price_eth: float = 0.0
    price_usd: float = 0.0
    market_cap_eth: float = 0.0
    market_cap_usd: float = 0.0
    volume_24h_eth: float = 0.0
    
    # ATH data
    ath_price_eth: float = 0.0
    ath_market_cap_eth: float = 0.0
    ath_net_buy_amount_eth: float = 0.0
    
    # Social/Visual
    image_url: str = ""
    website: str = ""
    twitter: str = ""
    telegram: str = ""
    has_image: bool = False
    has_socials: bool = False
    
    # Timestamps
    created_at: str = ""
    updated_at: str = ""
    
    @classmethod
    def from_dict(cls, data: dict) -> "NoxaToken":
        """Create NoxaToken from API response dict."""
        return cls(
            address=data.get("address", ""),
            chain=str(data.get("chainId", "")),
            name=data.get("name", ""),
            symbol=data.get("symbol", ""),
            description=data.get("description", ""),
            price_eth=data.get("priceEth", 0.0),
            price_usd=0.0,  # API doesn't return USD price directly
            market_cap_eth=data.get("marketCapEth", 0.0),
            market_cap_usd=0.0,  # API doesn't return USD market cap directly
            volume_24h_eth=data.get("volume24hEth", 0.0),
            ath_price_eth=data.get("athPriceEth", 0.0),
            ath_market_cap_eth=data.get("athMarketCapEth", 0.0),
            ath_net_buy_amount_eth=data.get("athNetBuyAmountEth", 0.0),
            image_url=data.get("logo", ""),
            website=data.get("website", ""),
            twitter=data.get("twitter", ""),
            telegram=data.get("telegram", ""),
            has_image=bool(data.get("logo", "")),
            has_socials=bool(data.get("twitter", "") or data.get("telegram", "")),
            created_at=data.get("createdAtTime", ""),
            updated_at=data.get("lastUpdated", ""),
        )
    
    @property
    def summary(self) -> str:
        """Human-readable summary."""
        mcap = self.market_cap_usd if self.market_cap_usd > 0 else self.market_cap_eth
        return f"🟢 {self.name} ({self.symbol}) — MCap: ${mcap:,.2f}"


@dataclass
class NoxaLaunchpadData:
    """Launchpad scan result combining NOXA Fun data with Chain Sentinel safety scan."""
    
    # NOXA Fun data
    noxa_token: NoxaToken
    
    # Chain Sentinel safety data
    safety_score: int = 0
    risk_level: str = "unknown"
    is_honeypot: Optional[bool] = None
    can_sell: Optional[bool] = None
    warnings: List[str] = field(default_factory=list)
    positives: List[str] = field(default_factory=list)
    
    @property
    def combined_summary(self) -> str:
        """Combined summary with safety and market data."""
        emoji = {"safe": "✅", "caution": "⚠️", "danger": "🔴", "critical": "🚨"}.get(
            self.risk_level, "❓"
        )
        return (
            f"{emoji} {self.noxa_token.name} ({self.noxa_token.symbol}) — "
            f"Safety: {self.safety_score}/100 | "
            f"MCap: ${self.noxa_token.market_cap_usd:,.2f}"
        )


class NoxaFunClient:
    """
    Client for NOXA Fun launchpad data.
    
    Usage:
        client = NoxaFunClient()
        tokens = await client.get_tokens("robinhood", sort="newest", limit=20)
    """
    
    def __init__(self, timeout: float = 30.0):
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=NOXA_FUN_BASE_URL,
                timeout=self.timeout,
                headers={
                    "User-Agent": "ChainSentinel/1.0",
                    "Accept": "application/json",
                },
            )
        return self._client
    
    async def close(self):
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    async def get_tokens(
        self,
        chain: str = "robinhood",
        sort: str = "newest",
        order: str = "desc",
        limit: int = 20,
        offset: int = 0,
        symbol: Optional[str] = None,
        has_image: Optional[bool] = None,
        has_socials: Optional[bool] = None,
        min_ath_price_eth: Optional[float] = None,
        min_ath_market_cap_eth: Optional[float] = None,
        min_market_cap_eth: Optional[float] = None,
        min_volume_24h_eth: Optional[float] = None,
        min_ath_net_buy_amount_eth: Optional[float] = None,
    ) -> List[NoxaToken]:
        """
        Get tokens from NOXA Fun launchpad.
        
        Args:
            chain: Blockchain network (robinhood, plasma, monad)
            sort: Sort field (newest, market_cap, volume, etc.)
            order: Sort order (asc, desc)
            limit: Number of results (max 100)
            offset: Pagination offset
            symbol: Filter by symbol
            has_image: Filter tokens with images
            has_socials: Filter tokens with socials
            min_ath_price_eth: Minimum ATH price in ETH
            min_ath_market_cap_eth: Minimum ATH market cap in ETH
            min_market_cap_eth: Minimum current market cap in ETH
            min_volume_24h_eth: Minimum 24h volume in ETH
            min_ath_net_buy_amount_eth: Minimum ATH net buy amount in ETH
        
        Returns:
            List of NoxaToken objects
        """
        client = await self._get_client()
        
        # Build query parameters
        params = {
            "sort": sort,
            "order": order,
            "limit": min(limit, 100),
            "offset": offset,
        }
        
        if symbol:
            params["symbol"] = symbol
        if has_image is not None:
            params["hasImage"] = str(has_image).lower()
        if has_socials is not None:
            params["hasSocials"] = str(has_socials).lower()
        if min_ath_price_eth is not None:
            params["minAthPriceEth"] = min_ath_price_eth
        if min_ath_market_cap_eth is not None:
            params["minAthMarketCapEth"] = min_ath_market_cap_eth
        if min_market_cap_eth is not None:
            params["minMarketCapEth"] = min_market_cap_eth
        if min_volume_24h_eth is not None:
            params["minVolume24hEth"] = min_volume_24h_eth
        if min_ath_net_buy_amount_eth is not None:
            params["minAthNetBuyAmountEth"] = min_ath_net_buy_amount_eth
        
        try:
            response = await client.get(f"/v1/{chain}/tokens", params=params)
            response.raise_for_status()
            data = response.json()
            
            # Parse response - API returns {"pagination": {...}, "tokens": [...]}
            if isinstance(data, dict):
                tokens_data = data.get("tokens", [])
            elif isinstance(data, list):
                tokens_data = data
            else:
                tokens_data = []
            return [NoxaToken.from_dict(t) for t in tokens_data]
        
        except httpx.HTTPStatusError as e:
            print(f"NOXA Fun API error: {e.response.status_code}")
            return []
        except Exception as e:
            print(f"NOXA Fun error: {e}")
            return []
    
    async def get_token_by_address(
        self,
        chain: str,
        address: str
    ) -> Optional[NoxaToken]:
        """Get a specific token by address."""
        tokens = await self.get_tokens(chain, limit=100)
        for token in tokens:
            if token.address.lower() == address.lower():
                return token
        return None
    
    async def get_trending_tokens(
        self,
        chain: str = "robinhood",
        limit: int = 10
    ) -> List[NoxaToken]:
        """Get trending tokens (highest volume)."""
        return await self.get_tokens(
            chain=chain,
            sort="volume",
            order="desc",
            limit=limit
        )
    
    async def get_new_tokens(
        self,
        chain: str = "robinhood",
        limit: int = 10
    ) -> List[NoxaToken]:
        """Get newest tokens."""
        return await self.get_tokens(
            chain=chain,
            sort="newest",
            order="desc",
            limit=limit
        )
    
    async def get_top_mcap_tokens(
        self,
        chain: str = "robinhood",
        limit: int = 10
    ) -> List[NoxaToken]:
        """Get tokens by market cap."""
        return await self.get_tokens(
            chain=chain,
            sort="market_cap",
            order="desc",
            limit=limit
        )


# Global client instance
noxafun_client = NoxaFunClient()
