"""
CoinMarketCap API Client — Chain Sentinel Integration
Free tier: 10,000 credits/month, 333 calls/day
"""

import httpx
import os
import time
from typing import Optional
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv()

CMC_BASE = "https://pro-api.coinmarketcap.com"
CMC_TRIAL_BASE = "https://pro-api.coinmarketcap.com"  # Same base, different key behavior


@dataclass
class CMCTokenData:
    """CMC data for a single token."""
    cmc_id: Optional[int] = None
    name: str = ""
    symbol: str = ""
    slug: str = ""
    cmc_rank: Optional[int] = None
    price_usd: float = 0.0
    percent_change_1h: float = 0.0
    percent_change_24h: float = 0.0
    percent_change_7d: float = 0.0
    percent_change_30d: float = 0.0
    market_cap: float = 0.0
    volume_24h: float = 0.0
    circulating_supply: float = 0.0
    total_supply: float = 0.0
    max_supply: Optional[float] = None
    logo: str = ""
    description: str = ""
    website: str = ""
    twitter: str = ""
    explorer: str = ""
    tags: list = field(default_factory=list)
    date_added: str = ""
    last_updated: str = ""


@dataclass
class CMCGlobalMetrics:
    """Global crypto market metrics."""
    total_market_cap: float = 0.0
    total_volume_24h: float = 0.0
    btc_dominance: float = 0.0
    eth_dominance: float = 0.0
    active_cryptocurrencies: int = 0
    total_currencies: int = 0
    active_exchanges: int = 0
    last_updated: str = ""


class CMCClient:
    """CoinMarketCap API client with caching and error handling."""

    def __init__(self):
        self.api_key = os.getenv("CMC_API_KEY", "")
        self.base_url = CMC_BASE
        self._cache: dict = {}
        self._cache_ttl = 300  # 5 min cache

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)

    def _headers(self) -> dict:
        return {
            "Accept": "application/json",
            "Accept-Encoding": "deflate, gzip",
            "X-CMC_PRO_API_KEY": self.api_key,
        }

    def _get_cached(self, key: str) -> Optional[dict]:
        if key in self._cache:
            data, ts = self._cache[key]
            if time.time() - ts < self._cache_ttl:
                return data
            del self._cache[key]
        return None

    def _set_cache(self, key: str, data: dict):
        self._cache[key] = (data, time.time())

    async def _get(self, endpoint: str, params: Optional[dict] = None) -> dict:
        """Make a GET request to CMC API."""
        if not self.enabled:
            return {"error": "CMC API key not configured"}

        cache_key = f"{endpoint}:{params}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        url = f"{self.base_url}{endpoint}"
        async with httpx.AsyncClient(timeout=15) as client:
            try:
                resp = await client.get(url, headers=self._headers(), params=params)
                resp.raise_for_status()
                data = resp.json()
                self._set_cache(cache_key, data)
                return data
            except httpx.HTTPStatusError as e:
                return {"error": f"CMC API error: {e.response.status_code}", "detail": str(e)}
            except Exception as e:
                return {"error": f"CMC request failed: {str(e)}"}

    async def get_token_by_contract(self, address: str, chain: str = "bsc") -> Optional[CMCTokenData]:
        """
        Look up a token by contract address using CMC's map endpoint.
        Returns CMCTokenData if found, None otherwise.
        """
        if not self.enabled:
            return None

        # Map our chain IDs to CMC platform IDs
        # CMC platform IDs (from /v1/cryptocurrency/map)
        platform_map = {
            "eth": "1027",      # Ethereum
            "bsc": "1839",      # BNB Smart Chain
            "polygon": "3890",  # Polygon
            "arbitrum": "11841", # Arbitrum
            "base": "27716",    # Base
            "avalanche": "5805", # Avalanche
            "fantom": "3513",   # Fantom
            "optimism": "11840", # Optimism
            "solana": "5426",   # Solana
        }

        platform_id = platform_map.get(chain)
        if not platform_id:
            return None

        # Search by contract address
        data = await self._get("/v2/cryptocurrency/info", {
            "address": address,
        })

        if "error" in data:
            return None

        tokens = data.get("data", {})
        if not tokens:
            return None

        # Find the token matching our chain
        for token_id, token_info in tokens.items():
            platform = token_info.get("platform", {})
            if platform and str(platform.get("id", "")) == platform_id:
                return self._parse_token_info(token_info)

            # If no platform info (native token), check by address match
            if not platform and address.lower() in str(token_info.get("contract_address", [])).lower():
                return self._parse_token_info(token_info)

        # Fallback: return first result if any
        for token_id, token_info in tokens.items():
            return self._parse_token_info(token_info)

        return None

    async def get_token_by_symbol(self, symbol: str) -> Optional[CMCTokenData]:
        """Look up a token by symbol (e.g., 'BTC', 'ETH')."""
        if not self.enabled:
            return None

        data = await self._get("/v2/cryptocurrency/info", {
            "symbol": symbol.upper(),
        })

        if "error" in data:
            return None

        tokens = data.get("data", {})
        if not tokens:
            return None

        # Return the highest market cap match
        for token_id, token_info in tokens.items():
            return self._parse_token_info(token_info)

        return None

    async def get_quote_by_id(self, cmc_id: int) -> Optional[dict]:
        """Get latest quote by CMC ID."""
        if not self.enabled:
            return None

        data = await self._get("/v2/cryptocurrency/quotes/latest", {
            "id": str(cmc_id),
            "convert": "USD",
        })

        if "error" in data:
            return None

        tokens = data.get("data", {})
        if str(cmc_id) in tokens:
            return tokens[str(cmc_id)]
        return None

    async def enrich_token(self, address: str, chain: str = "bsc") -> Optional[CMCTokenData]:
        """
        Enrich a token scan with CMC data.
        First tries contract address lookup, then symbol lookup.
        """
        if not self.enabled:
            return None

        # Try contract address first
        result = await self.get_token_by_contract(address, chain)
        if result:
            return result

        return None

    async def get_listings_latest(self, start: int = 1, limit: int = 100, sort: str = "market_cap") -> list:
        """Get latest cryptocurrency listings ranked by market cap."""
        if not self.enabled:
            return []

        data = await self._get("/v1/cryptocurrency/listings/latest", {
            "start": str(start),
            "limit": str(limit),
            "sort": sort,
            "convert": "USD",
        })

        if "error" in data:
            return []

        return data.get("data", [])

    async def get_trending_latest(self, limit: int = 20) -> list:
        """Get trending cryptocurrencies."""
        if not self.enabled:
            return []

        data = await self._get("/v1/cryptocurrency/trending/latest", {
            "limit": str(limit),
            "convert": "USD",
        })

        if "error" in data:
            return []

        return data.get("data", [])

    async def get_trending_gainers_losers(self, limit: int = 20, sort_dir: str = "desc") -> list:
        """Get top gainers or losers. sort_dir='desc' for gainers, 'asc' for losers."""
        if not self.enabled:
            return []

        data = await self._get("/v1/cryptocurrency/trending/gainers-losers", {
            "limit": str(limit),
            "sort_dir": sort_dir,
            "convert": "USD",
        })

        if "error" in data:
            return []

        return data.get("data", [])

    async def get_trending_most_visited(self, limit: int = 20) -> list:
        """Get most visited cryptocurrencies."""
        if not self.enabled:
            return []

        data = await self._get("/v1/cryptocurrency/trending/most-visited", {
            "limit": str(limit),
            "convert": "USD",
        })

        if "error" in data:
            return []

        return data.get("data", [])

    async def get_global_metrics(self) -> Optional[CMCGlobalMetrics]:
        """Get global crypto market metrics."""
        if not self.enabled:
            return None

        data = await self._get("/v1/global-metrics/quotes/latest", {
            "convert": "USD",
        })

        if "error" in data:
            return None

        d = data.get("data", {})
        quote = d.get("quote", {}).get("USD", {})

        return CMCGlobalMetrics(
            total_market_cap=quote.get("total_market_cap", 0),
            total_volume_24h=quote.get("total_volume_24h", 0),
            btc_dominance=d.get("btc_dominance", 0),
            eth_dominance=d.get("eth_dominance", 0),
            active_cryptocurrencies=d.get("active_cryptocurrencies", 0),
            total_currencies=d.get("total_currencies", 0),
            active_exchanges=d.get("active_exchanges", 0),
            last_updated=d.get("last_updated", ""),
        )

    async def get_new_listings(self, limit: int = 20) -> list:
        """Get newly listed cryptocurrencies."""
        if not self.enabled:
            return []

        data = await self._get("/v1/cryptocurrency/listings/new", {
            "limit": str(limit),
            "convert": "USD",
        })

        if "error" in data:
            return []

        return data.get("data", [])

    async def get_price_performance(self, cmc_id: int) -> Optional[dict]:
        """Get price performance stats for a token."""
        if not self.enabled:
            return None

        data = await self._get("/v2/cryptocurrency/price-performance-stats/latest", {
            "id": str(cmc_id),
            "convert": "USD",
        })

        if "error" in data:
            return None

        tokens = data.get("data", {})
        if str(cmc_id) in tokens:
            return tokens[str(cmc_id)]
        return None

    async def search_tokens(self, query: str) -> list:
        """Search for tokens by name or symbol using the map endpoint."""
        if not self.enabled:
            return []

        data = await self._get("/v1/cryptocurrency/map", {
            "listing_status": "active",
            "limit": "50",
        })

        if "error" in data:
            return []

        results = []
        query_lower = query.lower()
        for token in data.get("data", []):
            name = token.get("name", "").lower()
            symbol = token.get("symbol", "").lower()
            slug = token.get("slug", "").lower()
            if query_lower in name or query_lower in symbol or query_lower in slug:
                results.append(token)

        return results[:10]  # Return top 10 matches

    def _parse_token_info(self, info: dict) -> CMCTokenData:
        """Parse CMC token info response into CMCTokenData."""
        urls = info.get("urls", {})
        website = ""
        if urls.get("website"):
            website = urls["website"][0] if urls["website"] else ""

        twitter = ""
        if urls.get("twitter"):
            twitter = urls["twitter"][0] if urls["twitter"] else ""

        explorer = ""
        if urls.get("explorer"):
            explorer = urls["explorer"][0] if urls["explorer"] else ""

        return CMCTokenData(
            cmc_id=info.get("id"),
            name=info.get("name", ""),
            symbol=info.get("symbol", ""),
            slug=info.get("slug", ""),
            logo=info.get("logo", ""),
            description=info.get("description", ""),
            website=website,
            twitter=twitter,
            explorer=explorer,
            tags=info.get("tags", []),
            date_added=info.get("date_added", ""),
        )


# Singleton instance
cmc_client = CMCClient()
