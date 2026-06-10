"""
Chain Shield — Token Safety Scanner (Multi-chain)
Scans tokens across BSC, Ethereum, Base, Arbitrum, Polygon for rugpull/honeypot indicators.
"""

import httpx
import asyncio
import os
from cmc_client import cmc_client
from typing import Optional
from dataclasses import dataclass, field


# Chain configurations
CHAINS = {
    "bsc": {
        "name": "BNB Smart Chain",
        "goplus_id": "56",
        "dexscreener_slug": "bsc",
        "explorer": "https://bscscan.com",
        "native_token": "BNB",
        "color": "#F3BA2F",
        "icon": "🟡"
    },
    "eth": {
        "name": "Ethereum",
        "goplus_id": "1",
        "dexscreener_slug": "ethereum",
        "explorer": "https://etherscan.io",
        "native_token": "ETH",
        "color": "#627EEA",
        "icon": "🔷"
    },
    "base": {
        "name": "Base",
        "goplus_id": "8453",
        "dexscreener_slug": "base",
        "explorer": "https://basescan.org",
        "native_token": "ETH",
        "color": "#0052FF",
        "icon": "🔵"
    },
    "arbitrum": {
        "name": "Arbitrum One",
        "goplus_id": "42161",
        "dexscreener_slug": "arbitrum",
        "explorer": "https://arbiscan.io",
        "native_token": "ETH",
        "color": "#28A0F0",
        "icon": "🌀"
    },
    "polygon": {
        "name": "Polygon",
        "goplus_id": "137",
        "dexscreener_slug": "polygon",
        "explorer": "https://polygonscan.com",
        "native_token": "MATIC",
        "color": "#8247E5",
        "icon": "🟣"
    },
    "avalanche": {
        "name": "Avalanche",
        "goplus_id": "43114",
        "dexscreener_slug": "avalanche",
        "explorer": "https://snowtrace.io",
        "native_token": "AVAX",
        "color": "#E84142",
        "icon": "🔴"
    },
    "fantom": {
        "name": "Fantom",
        "goplus_id": "250",
        "dexscreener_slug": "fantom",
        "explorer": "https://ftmscan.com",
        "native_token": "FTM",
        "color": "#1969FF",
        "icon": "👻"
    },
    "optimism": {
        "name": "Optimism",
        "goplus_id": "10",
        "dexscreener_slug": "optimism",
        "explorer": "https://optimistic.etherscan.io",
        "native_token": "ETH",
        "color": "#FF0420",
        "icon": "🔴"
    },
    "solana": {
        "name": "Solana",
        "goplus_id": "solana",
        "dexscreener_slug": "solana",
        "explorer": "https://solscan.io",
        "native_token": "SOL",
        "color": "#9945FF",
        "icon": "🟣"
    }
}


@dataclass
class TokenReport:
    address: str
    chain: str = "bsc"
    name: str = ""
    symbol: str = ""
    
    # Safety indicators
    is_honeypot: Optional[bool] = None
    can_sell: Optional[bool] = None
    buy_tax: float = 0.0
    sell_tax: float = 0.0
    
    # Ownership
    owner_renounced: Optional[bool] = None
    owner_address: str = ""
    
    # Liquidity
    liquidity_locked: Optional[bool] = None
    lock_platform: str = ""
    lock_duration: str = ""
    
    # Contract
    is_verified: Optional[bool] = None
    is_proxy: Optional[bool] = None
    has_transfer_fee: Optional[bool] = None
    
    # Market data
    price_usd: float = 0.0
    volume_24h: float = 0.0
    market_cap: float = 0.0
    holders: int = 0
    pair_created: str = ""
    
    # Score
    safety_score: int = 0
    risk_level: str = ""
    data_sources: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    positives: list = field(default_factory=list)
    
    # Raw data for debugging
    raw_data: dict = field(default_factory=dict)


class TokenScanner:
    def __init__(self):
        self.goplus_base = "https://api.gopluslabs.io/api/v1"
        self.dexscreener_base = "https://api.dexscreener.com/latest/dex"
        self.gecko_base = "https://api.geckoterminal.com/api/v2"
    
    async def detect_chain(self, address: str) -> str:
        """Auto-detect which chain a token is on by checking all EVM chains + Solana."""
        import re
        
        # Solana format: base58, no 0x prefix
        if not re.match(r'^0x[0-9a-fA-F]{40}$', address):
            # Check if it looks like Solana
            if re.match(r'^[1-9A-HJ-NP-Za-km-z]{32,44}$', address):
                return "solana"
            return "bsc"  # fallback
        
        # EVM address — try chains in priority order (most popular first)
        evm_priority = ["bsc", "eth", "base", "arbitrum", "polygon", "avalanche", "fantom", "optimism"]
        
        async with httpx.AsyncClient(timeout=10) as client:
            for chain_id in evm_priority:
                try:
                    goplus_chain = CHAINS[chain_id]["goplus_id"]
                    url = f"{self.goplus_base}/token_security/{goplus_chain}?contract_addresses={address.lower()}"
                    resp = await client.get(url)
                    data = resp.json()
                    result = data.get("result", {})
                    token_data = result.get(address.lower(), {})
                    
                    # If we get any meaningful data, this is the right chain
                    if token_data and token_data.get("token_name"):
                        return chain_id
                except Exception:
                    continue
            
            # If GoPlus didn't find it, try DexScreener (it detects chain automatically)
            try:
                url = f"{self.dexscreener_base}/tokens/{address}"
                resp = await client.get(url)
                data = resp.json()
                pairs = data.get("pairs", [])
                if pairs:
                    detected_chain = pairs[0].get("chainId", "")
                    # Map dexscreener chainId to our chain keys
                    chain_map = {
                        "bsc": "bsc", "ethereum": "eth", "base": "base",
                        "arbitrum": "arbitrum", "polygon": "polygon",
                        "avalanche": "avalanche", "fantom": "fantom",
                        "optimism": "optimism", "solana": "solana"
                    }
                    return chain_map.get(detected_chain, "bsc")
            except Exception:
                pass
        
        return "bsc"  # ultimate fallback
    
    async def scan_token(self, address: str, chain: str = "bsc") -> TokenReport:
        """Main scan entry point — gathers all data and computes safety score."""
        # Auto-detect chain if not specified or if "auto"
        if chain == "auto":
            chain = await self.detect_chain(address)
        
        report = TokenReport(address=address, chain=chain)
        
        # Validate chain
        if chain not in CHAINS:
            report.warnings.append(f"Unsupported chain: {chain}")
            report.risk_level = "UNKNOWN"
            report.safety_score = 0
            return report
        
        # Validate address format
        if not self._validate_address(address, chain):
            report.warnings.append(f"Invalid address format for {CHAINS[chain]['name']}")
            report.risk_level = "UNKNOWN"
            report.safety_score = 0
            report.warnings.append("Please check the contract address and try again")
            return report
        
        # Run all checks in parallel
        goplus_task = self._check_goplus(address, chain)
        dex_task = self._check_dexscreener(address, chain)
        gecko_task = self._check_geckoterminal(address, chain)
        cmc_task = cmc_client.enrich_token(address, chain)
        
        goplus_data, dex_data, gecko_data = await asyncio.gather(
            goplus_task, dex_task, gecko_task,
            return_exceptions=True
        )

        # CMC runs separately (optional enrichment, not blocking)
        cmc_data = None
        try:
            cmc_data = await cmc_task
        except Exception:
            pass
        
        # Track data sources
        has_goplus = False
        has_dex = False
        has_gecko = False
        
        # Process GoPlus data
        if not isinstance(goplus_data, Exception) and goplus_data:
            self._process_goplus(report, goplus_data)
            has_goplus = True
            report.data_sources.append("GoPlus Security")
        
        # Process DexScreener data
        if not isinstance(dex_data, Exception) and dex_data:
            self._process_dexscreener(report, dex_data)
            has_dex = True
            report.data_sources.append("DexScreener")
        
        # Process GeckoTerminal data
        if not isinstance(gecko_data, Exception) and gecko_data:
            self._process_geckoterminal(report, gecko_data)
            has_gecko = True
            report.data_sources.append("GeckoTerminal")

        # Process CMC enrichment data (optional, enhances existing data)
        if cmc_data and not isinstance(cmc_data, Exception):
            self._process_cmc(report, cmc_data)
            report.data_sources.append("CoinMarketCap")
        
        # Check if we have enough data
        if not has_goplus and not has_dex:
            report.risk_level = "UNKNOWN"
            report.safety_score = 0
            report.warnings.append("⚠️ No security data available from GoPlus or DexScreener")
            report.warnings.append("This token may be very new, delisted, or not yet traded on DEXs")
            report.warnings.append("Exercise extreme caution — cannot verify safety")
            
            # Try to fetch on-chain data directly for Solana
            if chain == "solana":
                await self._fetch_solana_onchain(report, address)
        elif not has_goplus:
            report.warnings.append("ℹ️ GoPlus security data unavailable — score based on DexScreener only")
        elif not has_dex:
            report.warnings.append("ℹ️ DexScreener data unavailable — score based on GoPlus only")
        
        # Compute safety score
        if report.risk_level != "UNKNOWN":
            self._compute_score(report)
        
        return report
    
    def _validate_address(self, address: str, chain: str) -> bool:
        """Validate address format for the given chain."""
        import re
        if chain == "solana":
            # Solana: base58, 32-44 chars, no 0x prefix
            return bool(re.match(r'^[1-9A-HJ-NP-Za-km-z]{32,44}$', address))
        else:
            # EVM: 0x + 40 hex chars
            return bool(re.match(r'^0x[0-9a-fA-F]{40}$', address))
    
    async def _fetch_solana_onchain(self, report: TokenReport, address: str):
        """Fetch on-chain data directly from Solana RPC when APIs have no data."""
        rpc_url = "https://api.mainnet-beta.solana.com"
        
        async with httpx.AsyncClient(timeout=15) as client:
            try:
                # Get token supply
                supply_resp = await client.post(rpc_url, json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "getTokenSupply",
                    "params": [address]
                })
                supply_data = supply_resp.json()
                value = supply_data.get("result", {}).get("value", {})
                
                if value:
                    decimals = value.get("decimals", 0)
                    raw_supply = int(value.get("amount", 0))
                    report.raw_data["solana_supply"] = raw_supply
                    report.raw_data["solana_decimals"] = decimals
                    
                    # Store formatted supply as a pseudo-holder count for display
                    # (we'll show it as "Total Supply" in frontend)
                    report.holders = 0  # Can't get holder count from RPC
                    
                    # Add info about the token
                    report.warnings.append(f"📊 On-chain supply: {raw_supply / 10**decimals:,.0f} tokens ({decimals} decimals)")
                    report.warnings.append(f"🔗 Explorer: https://solscan.io/token/{address}")
                    
            except Exception:
                pass
    
    async def _check_goplus(self, address: str, chain: str) -> dict:
        """Check token via GoPlus Security API (free, no key needed)."""
        chain_id = CHAINS[chain]["goplus_id"]
        
        # Solana uses different address format (base58, not 0x)
        if chain == "solana":
            url = f"{self.goplus_base}/token_security/{chain_id}?contract_addresses={address}"
        else:
            url = f"{self.goplus_base}/token_security/{chain_id}?contract_addresses={address.lower()}"
        
        async with httpx.AsyncClient(timeout=15) as client:
            try:
                resp = await client.get(url)
                resp.raise_for_status()
                data = resp.json()
                result = data.get("result", {})
                # Solana addresses are case-sensitive, try both
                return result.get(address, result.get(address.lower(), {}))
            except Exception as e:
                return {}
    
    async def _check_dexscreener(self, address: str, chain: str) -> dict:
        """Check token pair data via DexScreener (free, no key needed)."""
        url = f"{self.dexscreener_base}/tokens/{address}"
        
        async with httpx.AsyncClient(timeout=15) as client:
            try:
                resp = await client.get(url)
                resp.raise_for_status()
                data = resp.json()
                pairs = data.get("pairs", [])
                
                # Filter pairs for the target chain
                chain_slug = CHAINS[chain]["dexscreener_slug"]
                chain_pairs = [p for p in pairs if p.get("chainId") == chain_slug]
                
                if chain_pairs:
                    return chain_pairs[0]
                elif pairs:
                    return pairs[0]
                return {}
            except Exception:
                return {}
    
    def _process_goplus(self, report: TokenReport, data: dict):
        """Process GoPlus Security data into report."""
        report.raw_data["goplus"] = data
        
        # Honeypot detection
        report.is_honeypot = data.get("is_honeypot") == "1"
        
        # Can sell — if field exists, use it; otherwise infer from honeypot
        can_sell_raw = data.get("is_can_sell")
        if can_sell_raw is not None:
            report.can_sell = can_sell_raw == "1"
        else:
            report.can_sell = not report.is_honeypot
        
        # Tax
        try:
            report.buy_tax = float(data.get("buy_tax", "0"))
            report.sell_tax = float(data.get("sell_tax", "0"))
        except (ValueError, TypeError):
            pass
        
        # Ownership
        report.owner_renounced = data.get("owner_change_balance") == "0"
        report.owner_address = data.get("owner_address", "")
        if data.get("owner_address") == "0x0000000000000000000000000000000000000000":
            report.owner_renounced = True
        
        # Contract verification
        report.is_verified = data.get("is_open_source") == "1"
        report.is_proxy = data.get("is_proxy") == "1"
        
        # Transfer fee
        report.has_transfer_fee = data.get("transfer_pausable") == "1"
        
        # Holders
        try:
            report.holders = int(data.get("holder_count", 0))
        except (ValueError, TypeError):
            pass
        
        # Red flags
        if data.get("hidden_owner") == "1":
            report.warnings.append("Hidden owner detected")
        if data.get("can_take_back_ownership") == "1":
            report.warnings.append("Ownership can be regained")
        if data.get("selfdestruct") == "1":
            report.warnings.append("Contract has self-destruct function")
        if data.get("external_call") == "1":
            report.warnings.append("External call detected (potential exploit vector)")
        if data.get("is_blacklisted") == "1":
            report.warnings.append("Blacklist function present")
        if data.get("is_whitelisted") == "1":
            report.warnings.append("Whitelist function present")
        if data.get("is_anti_whale") == "1":
            report.warnings.append("Anti-whale mechanism (can restrict selling)")
        if data.get("trading_cooldown") == "1":
            report.warnings.append("Trading cooldown active")
    
    def _process_dexscreener(self, report: TokenReport, data: dict):
        """Process DexScreener data into report."""
        report.raw_data["dexscreener"] = data
        
        # Basic info
        report.name = data.get("baseToken", {}).get("name", report.name)
        report.symbol = data.get("baseToken", {}).get("symbol", report.symbol)
        
        # Price and market data
        try:
            report.price_usd = float(data.get("priceUsd", 0))
            report.volume_24h = float(data.get("volume", {}).get("h24", 0))
            report.market_cap = float(data.get("marketCap", 0) or data.get("fdv", 0))
        except (ValueError, TypeError):
            pass
        
        # Pair info
        report.pair_created = data.get("pairCreatedAt", "")
    
    async def _check_geckoterminal(self, address: str, chain: str) -> dict:
        """Check token via GeckoTerminal API (free, no key needed)."""
        # GeckoTerminal chain network slugs
        gecko_networks = {
            "bsc": "bsc", "eth": "ethereum", "base": "base",
            "arbitrum": "arbitrum", "polygon": "polygon",
            "avalanche": "avax", "fantom": "fantom",
            "optimism": "optimism", "solana": "solana"
        }
        network = gecko_networks.get(chain, "bsc")
        url = f"{self.gecko_base}/networks/{network}/tokens/{address}"
        
        async with httpx.AsyncClient(timeout=15) as client:
            try:
                resp = await client.get(url)
                if resp.status_code == 200:
                    data = resp.json()
                    return data.get("data", {})
            except Exception:
                pass
        return {}
    
    def _process_geckoterminal(self, report: TokenReport, data: dict):
        """Process GeckoTerminal data into report."""
        attrs = data.get("attributes", {})
        if not attrs:
            return
        
        report.raw_data["geckoterminal"] = attrs
        
        # Price (if not already set from DexScreener)
        if not report.price_usd:
            try:
                report.price_usd = float(attrs.get("price_usd", 0))
            except (ValueError, TypeError):
                pass
        
        # Market cap (if not already set)
        if not report.market_cap:
            try:
                report.market_cap = float(attrs.get("market_cap_usd", 0) or 0)
            except (ValueError, TypeError):
                pass
        
        # Volume (if not already set)
        if not report.volume_24h:
            try:
                report.volume_24h = float(attrs.get("volume_usd", {}).get("h24", 0) or 0)
            except (ValueError, TypeError):
                pass
        
        # Liquidity
        if report.liquidity_locked is None:
            liq = attrs.get("liquidity_usd", {})
            if liq:
                report.positives.append(f"💧 Liquidity: ${float(liq or 0):,.0f}")

    def _process_cmc(self, report: TokenReport, cmc_data):
        """Enrich report with CoinMarketCap data."""
        from cmc_client import CMCTokenData

        if not isinstance(cmc_data, CMCTokenData):
            return

        # Enrich name/symbol if missing
        if not report.name and cmc_data.name:
            report.name = cmc_data.name
        if not report.symbol and cmc_data.symbol:
            report.symbol = cmc_data.symbol

        # Store CMC metadata in raw_data
        report.raw_data["cmc"] = {
            "id": cmc_data.cmc_id,
            "rank": cmc_data.cmc_rank,
            "slug": cmc_data.slug,
            "logo": cmc_data.logo,
            "description": cmc_data.description[:200] if cmc_data.description else "",
            "website": cmc_data.website,
            "twitter": cmc_data.twitter,
            "explorer": cmc_data.explorer,
            "tags": cmc_data.tags,
            "percent_change_1h": cmc_data.percent_change_1h,
            "percent_change_24h": cmc_data.percent_change_24h,
            "percent_change_7d": cmc_data.percent_change_7d,
            "percent_change_30d": cmc_data.percent_change_30d,
        }

        # CMC rank as a positive signal
        if cmc_data.cmc_rank and cmc_data.cmc_rank <= 100:
            report.positives.append(f"🏆 CMC Rank #{cmc_data.cmc_rank} — Top 100 token")
        elif cmc_data.cmc_rank and cmc_data.cmc_rank <= 500:
            report.positives.append(f"📊 CMC Rank #{cmc_data.cmc_rank}")
    
    def _compute_score(self, report: TokenReport):
        """Compute safety score 0-100. Higher = safer."""
        score = 100
        
        # === CRITICAL ISSUES ===
        if report.is_honeypot:
            score -= 50
            report.warnings.append("🍯 HONEYPOT DETECTED — You CANNOT sell this token!")
        
        if report.can_sell is False and report.is_honeypot is None:
            score -= 40
            report.warnings.append("🚫 Selling appears to be blocked")
        
        # === HIGH ISSUES ===
        if report.sell_tax and report.sell_tax > 0.1:
            score -= 25
            report.warnings.append(f"💸 Sell tax is {report.sell_tax*100:.1f}% — you lose {report.sell_tax*100:.1f}% when selling")
        elif report.sell_tax and report.sell_tax > 0.05:
            score -= 15
            report.warnings.append(f"💸 Sell tax is {report.sell_tax*100:.1f}%")
        
        if report.buy_tax and report.buy_tax > 0.1:
            score -= 20
            report.warnings.append(f"💸 Buy tax is {report.buy_tax*100:.1f}%")
        
        if report.owner_renounced is False:
            score -= 20
            report.warnings.append("👤 Owner has NOT renounced — can modify contract")
        elif report.owner_renounced is True:
            report.positives.append("✅ Owner has renounced ownership")
        
        # === MEDIUM ISSUES ===
        if report.is_verified is False:
            score -= 15
            report.warnings.append("⚠️ Contract source code NOT verified")
        elif report.is_verified is True:
            report.positives.append("✅ Contract source code verified")
        
        if report.is_proxy:
            score -= 10
            report.warnings.append("⚠️ Contract is a proxy — can be upgraded/changed")
        
        if report.has_transfer_fee:
            score -= 10
            report.warnings.append("⚠️ Transfer can be paused")
        
        if report.liquidity_locked is False:
            score -= 15
            report.warnings.append("💧 Liquidity NOT locked — team can pull it")
        elif report.liquidity_locked is True:
            report.positives.append("✅ Liquidity is locked")
        
        # === LOW ISSUES ===
        if report.holders and report.holders < 50:
            score -= 5
            report.warnings.append(f"👥 Low holder count: {report.holders}")
        elif report.holders and report.holders > 500:
            report.positives.append(f"✅ {report.holders:,} holders")
        
        if report.volume_24h and report.volume_24h < 1000:
            score -= 5
            report.warnings.append("📊 Very low 24h volume")
        elif report.volume_24h and report.volume_24h > 100000:
            report.positives.append(f"✅ Strong 24h volume: ${report.volume_24h:,.0f}")
        
        # === POSITIVE BONUSES ===
        if report.sell_tax == 0 and report.buy_tax == 0:
            report.positives.append("✅ Zero buy/sell tax")
        
        # Clamp score
        report.safety_score = max(0, min(100, score))
        
        # Risk level
        if report.safety_score >= 80:
            report.risk_level = "LOW"
        elif report.safety_score >= 60:
            report.risk_level = "MEDIUM"
        elif report.safety_score >= 40:
            report.risk_level = "HIGH"
        else:
            report.risk_level = "CRITICAL"


def get_supported_chains():
    """Return list of supported chains for API responses."""
    return {
        chain_id: {
            "name": info["name"],
            "icon": info["icon"],
            "native_token": info["native_token"],
            "explorer": info["explorer"]
        }
        for chain_id, info in CHAINS.items()
    }
