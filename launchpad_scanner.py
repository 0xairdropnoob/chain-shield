"""
Chain Sentinel — Launchpad Scanner
Aggregate new tokens from pump.fun, gmgn, four.meme, bankr, birdeye.
"""

import asyncio
import aiohttp
import time
from dataclasses import dataclass
from typing import Optional


# === DATA SOURCES ===

DEXSCREENER_BASE = "https://api.dexscreener.com"
BIRDEYE_BASE = "https://public-api.birdeye.so"

# Known launchpad program/contract addresses
PUMP_FUN_PROGRAM = "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P"

# Solana RPC
SOLANA_RPC = "https://api.mainnet-beta.solana.com"


@dataclass
class LaunchpadToken:
    """Represents a new token from a launchpad."""
    address: str
    chain: str
    launchpad: str  # pump.fun, gmgn, four.meme, bankr, birdeye, dexscreener
    name: str
    symbol: str
    price_usd: float
    market_cap: float
    volume_24h: float
    volume_6h: float = 0.0
    volume_1h: float = 0.0
    liquidity_usd: float = 0.0
    holders: int = 0
    created_at: int = 0  # unix timestamp
    pair_address: str = ""
    bonding_curve_pct: float = 0.0  # pump.fun bonding curve progress
    dex: str = ""
    website: str = ""
    twitter: str = ""
    telegram: str = ""
    buy_count_24h: int = 0
    sell_count_24h: int = 0
    price_change_5m: float = 0.0
    price_change_1h: float = 0.0
    price_change_24h: float = 0.0
    rug_score: int = 0  # 0-100, higher = safer
    dev_wallet: str = ""
    top_10_hold_pct: float = 0.0


class LaunchpadScanner:
    """Scan and aggregate tokens from multiple launchpads."""

    def __init__(self):
        self.session = None

    async def _get_session(self):
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=15),
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
                    "Accept": "application/json",
                }
            )
        return self.session

    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()

    # === DexScreener (FREE, no API key) ===

    async def _fetch_dexscreener(self, endpoint: str) -> dict:
        """Generic DexScreener API call."""
        session = await self._get_session()
        try:
            async with session.get(f"{DEXSCREENER_BASE}{endpoint}") as resp:
                if resp.status == 200:
                    return await resp.json()
                return {}
        except Exception as e:
            print(f"DexScreener error: {e}")
            return {}

    async def get_dexscreener_trending(self, limit: int = 20) -> list:
        """Get trending tokens from DexScreener."""
        data = await self._fetch_dexscreener("/token-profiles/latest/v1")
        tokens = []

        if isinstance(data, list):
            seen = set()
            unique_items = []
            for item in data:
                addr = item.get("tokenAddress", "")
                if addr and addr not in seen:
                    seen.add(addr)
                    unique_items.append(item)

            for item in unique_items[:limit]:
                token_addr = item.get("tokenAddress", "")
                chain = item.get("chainId", "unknown")

                # Get pair data for price/volume
                pair_data = await self._fetch_dexscreener(f"/latest/dex/tokens/{token_addr}")
                pairs = pair_data.get("pairs", [])

                if pairs:
                    pair = max(pairs, key=lambda p: float(p.get("liquidity", {}).get("usd", 0) or 0))
                    base = pair.get("baseToken", {})

                    tokens.append(LaunchpadToken(
                        address=token_addr,
                        chain=chain,
                        launchpad="dexscreener",
                        name=base.get("name", "Unknown"),
                        symbol=base.get("symbol", "???"),
                        price_usd=float(pair.get("priceUsd", 0) or 0),
                        market_cap=float(pair.get("marketCap", 0) or 0),
                        volume_24h=float(pair.get("volume", {}).get("h24", 0) or 0),
                        volume_6h=float(pair.get("volume", {}).get("h6", 0) or 0),
                        volume_1h=float(pair.get("volume", {}).get("h1", 0) or 0),
                        liquidity_usd=float(pair.get("liquidity", {}).get("usd", 0) or 0),
                        pair_address=pair.get("pairAddress", ""),
                        dex=pair.get("dexId", ""),
                        price_change_5m=float(pair.get("priceChange", {}).get("m5", 0) or 0),
                        price_change_1h=float(pair.get("priceChange", {}).get("h1", 0) or 0),
                        price_change_24h=float(pair.get("priceChange", {}).get("h24", 0) or 0),
                        buy_count_24h=int(pair.get("txns", {}).get("h24", {}).get("buys", 0) or 0),
                        sell_count_24h=int(pair.get("txns", {}).get("h24", {}).get("sells", 0) or 0),
                    ))

                # Rate limit: DexScreener allows ~300 req/min
                await asyncio.sleep(0.2)

        return tokens

    async def get_dexscreener_boosted(self, limit: int = 20) -> list:
        """Get boosted/trending tokens from DexScreener."""
        data = await self._fetch_dexscreener("/token-boosts/latest/v1")
        tokens = []

        if isinstance(data, list):
            # Collect unique token addresses
            seen = set()
            unique_items = []
            for item in data:
                addr = item.get("tokenAddress", "")
                if addr and addr not in seen:
                    seen.add(addr)
                    unique_items.append(item)

            for item in unique_items[:limit]:
                token_addr = item.get("tokenAddress", "")
                chain = item.get("chainId", "unknown")

                # Get pair data
                pair_data = await self._fetch_dexscreener(f"/latest/dex/tokens/{token_addr}")
                pairs = pair_data.get("pairs", [])

                if pairs:
                    pair = max(pairs, key=lambda p: float(p.get("liquidity", {}).get("usd", 0) or 0))
                    base = pair.get("baseToken", {})
                    info = pair.get("info", {})
                    links = item.get("links", [])

                    # Extract social links from boost data
                    website = ""
                    twitter = ""
                    telegram = ""
                    for link in links:
                        url = link.get("url", "")
                        if link.get("type") == "twitter" or "x.com" in url:
                            twitter = url
                        elif link.get("type") == "telegram" or "t.me" in url:
                            telegram = url
                        elif url and not link.get("type"):
                            website = url

                    tokens.append(LaunchpadToken(
                        address=token_addr,
                        chain=chain,
                        launchpad="dexscreener",
                        name=base.get("name", "Unknown"),
                        symbol=base.get("symbol", "???"),
                        price_usd=float(pair.get("priceUsd", 0) or 0),
                        market_cap=float(pair.get("marketCap", 0) or 0),
                        volume_24h=float(pair.get("volume", {}).get("h24", 0) or 0),
                        volume_1h=float(pair.get("volume", {}).get("h1", 0) or 0),
                        liquidity_usd=float(pair.get("liquidity", {}).get("usd", 0) or 0),
                        pair_address=pair.get("pairAddress", ""),
                        dex=pair.get("dexId", ""),
                        price_change_1h=float(pair.get("priceChange", {}).get("h1", 0) or 0),
                        price_change_24h=float(pair.get("priceChange", {}).get("h24", 0) or 0),
                        buy_count_24h=int(pair.get("txns", {}).get("h24", {}).get("buys", 0) or 0),
                        sell_count_24h=int(pair.get("txns", {}).get("h24", {}).get("sells", 0) or 0),
                        website=website or (info.get("websites", [{}])[0].get("url", "") if info.get("websites") else ""),
                        twitter=twitter or (info.get("socials", [{}])[0].get("url", "") if info.get("socials") else ""),
                        telegram=telegram,
                    ))

                await asyncio.sleep(0.25)  # Rate limit

        return tokens

    # === Pump.fun (Solana) ===

    async def get_pumpfun_tokens(self, limit: int = 20) -> list:
        """Get new tokens from pump.fun."""
        session = await self._get_session()
        tokens = []

        try:
            # Pump.fun has an internal API for new tokens
            async with session.get(
                "https://frontend-api-v3.pump.fun/coins?offset=0&limit=50&sort=created_timestamp&order=DESC&includeNsfw=false"
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if isinstance(data, list):
                        for item in data[:limit]:
                            mint = item.get("mint", "")
                            created = int(item.get("created_timestamp", 0) / 1000) if item.get("created_timestamp") else 0

                            # Calculate bonding curve %
                            total_supply = float(item.get("total_supply", 1000000000))
                            usdc_threshold = float(item.get("usdc_threshold", 85000))
                            virtual_sol_reserves = float(item.get("virtual_sol_reserves", 0))
                            virtual_token_reserves = float(item.get("virtual_token_reserves", 0))

                            # Bonding curve progress (how close to Raydium graduation)
                            # Pump.fun graduates at ~$69K market cap
                            market_cap_sol = (virtual_sol_reserves / virtual_token_reserves * total_supply) / 1e9 if virtual_token_reserves > 0 else 0
                            bonding_pct = min(100, (market_cap_sol / 69000) * 100) if market_cap_sol > 0 else 0

                            tokens.append(LaunchpadToken(
                                address=mint,
                                chain="solana",
                                launchpad="pump.fun",
                                name=item.get("name", "Unknown"),
                                symbol=item.get("symbol", "???"),
                                price_usd=float(item.get("usd_market_cap", 0) or 0) / max(total_supply, 1),
                                market_cap=float(item.get("usd_market_cap", 0) or 0),
                                volume_24h=0,  # New tokens don't have 24h volume yet
                                holders=int(item.get("reply_count", 0) or 0),
                                created_at=created,
                                bonding_curve_pct=round(bonding_pct, 1),
                                dev_wallet=item.get("trump", ""),  # creator field
                                website=item.get("website", ""),
                                twitter=item.get("twitter", ""),
                                telegram=item.get("telegram", ""),
                            ))
                else:
                    print(f"Pump.fun API returned {resp.status}")
        except Exception as e:
            print(f"Pump.fun error: {e}")

        return tokens

    # === GMGN (Solana) via DexScreener fallback ===

    async def get_gmgn_trending(self, limit: int = 20) -> list:
        """Get trending Solana tokens (gmgn.ai has Cloudflare, using DexScreener fallback)."""
        session = await self._get_session()
        tokens = []

        try:
            # gmgn.ai has Cloudflare protection, use DexScreener for Solana trending
            async with session.get(
                "https://api.dexscreener.com/latest/dex/search?q=solana%20meme"
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    pairs = data.get("pairs", [])

                    # Filter Solana pairs only, sort by volume
                    sol_pairs = [p for p in pairs if p.get("chainId") == "solana"]
                    sol_pairs.sort(key=lambda p: float(p.get("volume", {}).get("h24", 0) or 0), reverse=True)

                    seen = set()
                    for pair in sol_pairs[:limit * 2]:
                        base = pair.get("baseToken", {})
                        addr = base.get("address", "")
                        if addr in seen:
                            continue
                        seen.add(addr)

                        tokens.append(LaunchpadToken(
                            address=addr,
                            chain="solana",
                            launchpad="gmgn",
                            name=base.get("name", "Unknown"),
                            symbol=base.get("symbol", "???"),
                            price_usd=float(pair.get("priceUsd", 0) or 0),
                            market_cap=float(pair.get("marketCap", 0) or 0),
                            volume_24h=float(pair.get("volume", {}).get("h24", 0) or 0),
                            volume_1h=float(pair.get("volume", {}).get("h1", 0) or 0),
                            liquidity_usd=float(pair.get("liquidity", {}).get("usd", 0) or 0),
                            holders=int(pair.get("info", {}).get("holders", 0) or 0) if pair.get("info") else 0,
                            pair_address=pair.get("pairAddress", ""),
                            dex=pair.get("dexId", ""),
                            price_change_1h=float(pair.get("priceChange", {}).get("h1", 0) or 0),
                            price_change_24h=float(pair.get("priceChange", {}).get("h24", 0) or 0),
                            buy_count_24h=int(pair.get("txns", {}).get("h24", {}).get("buys", 0) or 0),
                            sell_count_24h=int(pair.get("txns", {}).get("h24", {}).get("sells", 0) or 0),
                        ))

                        if len(tokens) >= limit:
                            break
                else:
                    print(f"DexScreener Solana search returned {resp.status}")
        except Exception as e:
            print(f"GMGN fallback error: {e}")

        return tokens

    # === Four.meme (BNB Chain) via DexScreener ===

    async def get_fourmeme_tokens(self, limit: int = 20) -> list:
        """Get new tokens from four.meme via DexScreener (four.meme API changed)."""
        session = await self._get_session()
        tokens = []

        try:
            # Use DexScreener to find four.meme tokens on BNB chain
            async with session.get(
                "https://api.dexscreener.com/latest/dex/search?q=four.meme"
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    pairs = data.get("pairs", [])

                    seen = set()
                    for pair in pairs[:limit * 2]:
                        base = pair.get("baseToken", {})
                        addr = base.get("address", "")
                        if addr in seen:
                            continue
                        seen.add(addr)

                        tokens.append(LaunchpadToken(
                            address=addr,
                            chain=pair.get("chainId", "bsc"),
                            launchpad="four.meme",
                            name=base.get("name", "Unknown"),
                            symbol=base.get("symbol", "???"),
                            price_usd=float(pair.get("priceUsd", 0) or 0),
                            market_cap=float(pair.get("marketCap", 0) or 0),
                            volume_24h=float(pair.get("volume", {}).get("h24", 0) or 0),
                            volume_1h=float(pair.get("volume", {}).get("h1", 0) or 0),
                            liquidity_usd=float(pair.get("liquidity", {}).get("usd", 0) or 0),
                            pair_address=pair.get("pairAddress", ""),
                            dex=pair.get("dexId", ""),
                            price_change_1h=float(pair.get("priceChange", {}).get("h1", 0) or 0),
                            price_change_24h=float(pair.get("priceChange", {}).get("h24", 0) or 0),
                            buy_count_24h=int(pair.get("txns", {}).get("h24", {}).get("buys", 0) or 0),
                            sell_count_24h=int(pair.get("txns", {}).get("h24", {}).get("sells", 0) or 0),
                        ))

                        if len(tokens) >= limit:
                            break
                else:
                    print(f"DexScreener four.meme search returned {resp.status}")
        except Exception as e:
            print(f"Four.meme error: {e}")

        return tokens

    # === UNIFIED FEED ===

    async def get_all_launchpad_tokens(
        self,
        launchpads: list = None,
        chains: list = None,
        limit_per_source: int = 10,
        is_pro: bool = False,
    ) -> dict:
        """
        Get new tokens from all launchpads.
        Free tier: 1 launchpad (dexscreener), delayed, limited.
        Pro tier: all 5 launchpads, real-time.
        """
        if launchpads is None:
            if is_pro:
                launchpads = ["dexscreener", "pump.fun", "gmgn", "four.meme"]
            else:
                launchpads = ["dexscreener"]

        results = {}
        all_tokens = []

        # Fetch from each launchpad concurrently
        tasks = {}
        for lp in launchpads:
            if lp == "dexscreener":
                tasks["dexscreener"] = self.get_dexscreener_boosted(limit=limit_per_source)
            elif lp == "pump.fun":
                tasks["pump.fun"] = self.get_pumpfun_tokens(limit=limit_per_source)
            elif lp == "gmgn":
                tasks["gmgn"] = self.get_gmgn_trending(limit=limit_per_source)
            elif lp == "four.meme":
                tasks["four.meme"] = self.get_fourmeme_tokens(limit=limit_per_source)

        # Run all fetches concurrently
        for name, coro in tasks.items():
            try:
                tokens = await coro
                results[name] = [self._token_to_dict(t, is_pro) for t in tokens]
                all_tokens.extend(tokens)
            except Exception as e:
                results[name] = {"error": str(e)}

        # Sort all tokens by volume/market_cap
        all_tokens.sort(key=lambda t: t.volume_24h or t.volume_1h or 0, reverse=True)

        # Build unified feed
        unified = [self._token_to_dict(t, is_pro) for t in all_tokens[:limit_per_source * len(launchpads)]]

        return {
            "launchpads_scanned": launchpads,
            "plan": "pro" if is_pro else "free",
            "total_tokens": len(unified),
            "tokens": unified if is_pro else unified[:5],  # Free: only 5 tokens
            "by_launchpad": results,
            "upgrade_message": None if is_pro else "Upgrade to Pro to see all launchpads, real-time data, and full token details."
        }

    def _token_to_dict(self, token: LaunchpadToken, is_pro: bool = False) -> dict:
        """Convert LaunchpadToken to dict, applying tier restrictions."""
        base = {
            "address": token.address[:8] + "..." if not is_pro else token.address,
            "chain": token.chain,
            "launchpad": token.launchpad,
            "name": token.name,
            "symbol": token.symbol,
            "price_usd": round(token.price_usd, 8) if is_pro else "***",
            "market_cap": round(token.market_cap, 2) if is_pro else "***",
        }

        if is_pro:
            base.update({
                "volume_24h": round(token.volume_24h, 2),
                "volume_1h": round(token.volume_1h, 2),
                "liquidity_usd": round(token.liquidity_usd, 2),
                "holders": token.holders,
                "created_at": token.created_at,
                "pair_address": token.pair_address,
                "bonding_curve_pct": token.bonding_curve_pct,
                "dex": token.dex,
                "price_change_5m": token.price_change_5m,
                "price_change_1h": token.price_change_1h,
                "price_change_24h": token.price_change_24h,
                "buy_count_24h": token.buy_count_24h,
                "sell_count_24h": token.sell_count_24h,
                "top_10_hold_pct": token.top_10_hold_pct,
                "website": token.website,
                "twitter": token.twitter,
                "telegram": token.telegram,
            })

        return base
