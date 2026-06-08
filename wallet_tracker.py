"""
Chain Sentinel — Smart Wallet Tracker
Track wallet trades, PnL, and holdings across EVM + Solana chains.
"""

import asyncio
import aiohttp
import time
from dataclasses import dataclass, field
from typing import Optional


# === RPC ENDPOINTS ===
RPC_ENDPOINTS = {
    "bsc": "https://bsc-dataseed.binance.org",
    "eth": "https://rpc.eth.gateway.fm",
    "base": "https://base.llamarpc.com",
    "arbitrum": "https://arb1.arbitrum.io/rpc",
    "polygon": "https://polygon-bor-rpc.publicnode.com",
    "avalanche": "https://api.avax.network/ext/bc/C/rpc",
    "fantom": "https://rpc.ftm.tools",
    "optimism": "https://mainnet.optimism.io",
    "solana": "https://api.mainnet-beta.solana.com",
}

# DEX Router addresses for trade detection
DEX_ROUTERS = {
    "bsc": {
        "0x10ed43c718714eb63d5aa57b78b54704e256024e": "PancakeSwap V2",
        "0x13f4ea83d0bd40e75c8222255bc855a974568dd4": "PancakeSwap V3",
        "0x1b02da8cb0d097eb8d57a175b88c7d8b47997506": "SushiSwap",
    },
    "eth": {
        "0x7a250d5630b4cf539739df2c5dacb4c659f2488d": "Uniswap V2",
        "0xe592427a0aece92de3edee1f18e0157c05861564": "Uniswap V3",
        "0x68b3465833fb72a70ecdf485e0e4c7bd8665fc45": "Uniswap V3 Router",
        "0xef1c6e67703c7bd7107eed8303fbe6ec2554bf6b": "Uniswap Universal Router",
    },
    "base": {
        "0x2626664c2603336e57b271c5c0b26f421741e481": "Uniswap V3",
        "0x4752ba5dbc23f44d87826276bf6fd6b1c372ad24": "Uniswap V2",
    },
    "arbitrum": {
        "0x68b3465833fb72a70ecdf485e0e4c7bd8665fc45": "Uniswap V3",
        "0x1b02da8cb0d097eb8d57a175b88c7d8b47997506": "SushiSwap",
    },
    "polygon": {
        "0x68b3465833fb72a70ecdf485e0e4c7bd8665fc45": "Uniswap V3",
        "0x1b02da8cb0d097eb8d57a175b88c7d8b47997506": "SushiSwap",
        "0xa5e0829caced8ffdd4de3c43696c57f7d7a678ff": "QuickSwap",
    },
}

# WETH/WBNB addresses for base pair detection
WRAPPED_NATIVE = {
    "bsc": "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c",
    "eth": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
    "base": "0x4200000000000000000000000000000000000006",
    "arbitrum": "0x82aF49447D8a07e3bd95BD0d56f35241523fBab1",
    "polygon": "0x0d500B1d8E8eF31E21C99d1Db9A6444d3ADf1270",
    "avalanche": "0xB31f66AA3C1e785363F0875A1B74E27b85FD66c7",
    "fantom": "0x21be370D5312f44cB42ce377BC9b8a0cEF1A4C83",
    "optimism": "0x4200000000000000000000000000000000000006",
}

# Transfer event topic
TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"

# DexScreener API (free, no key)
DEXSCREENER_API = "https://api.dexscreener.com/latest/dex"

# Etherscan V2 API (unified endpoint, supports multiple chains)
ETHERSCAN_V2_API = "https://api.etherscan.io/v2/api"

# Chain IDs for Etherscan V2
CHAIN_IDS = {
    "eth": 1,
    "bsc": 56,
    "polygon": 137,
    "arbitrum": 42161,
    "base": 8453,
    "optimism": 10,
    "avalanche": 43114,
}


@dataclass
class Trade:
    tx_hash: str
    chain: str
    timestamp: int
    action: str  # "buy" or "sell"
    token_address: str
    token_symbol: str
    token_name: str
    amount: float
    amount_usd: float
    price_usd: float
    dex: str
    pair_address: str = ""


@dataclass
class TokenHolding:
    token_address: str
    token_symbol: str
    token_name: str
    balance: float
    value_usd: float
    price_usd: float
    chain: str


@dataclass
class WalletPnL:
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    total_realized_pnl: float
    total_unrealized_pnl: float
    total_pnl: float
    best_trade: Optional[Trade] = None
    worst_trade: Optional[Trade] = None
    avg_hold_time_hours: float = 0.0


@dataclass
class WalletSummary:
    address: str
    chains: list
    total_value_usd: float
    pnl: WalletPnL
    recent_trades: list
    holdings: list


class WalletTracker:
    """Track wallet activity across EVM and Solana chains."""

    def __init__(self):
        self.session = None

    async def _get_session(self):
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=15),
                headers={"User-Agent": "ChainSentinel/0.5.0"}
            )
        return self.session

    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()

    # === EVM RPC CALLS ===

    async def _evm_rpc(self, chain: str, method: str, params: list) -> dict:
        """Make an EVM JSON-RPC call."""
        session = await self._get_session()
        url = RPC_ENDPOINTS.get(chain)
        if not url:
            return {"error": f"No RPC for chain {chain}"}

        payload = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
        try:
            async with session.post(url, json=payload) as resp:
                data = await resp.json()
                return data.get("result", data)
        except Exception as e:
            return {"error": str(e)}

    async def _get_latest_block(self, chain: str) -> int:
        """Get latest block number for a chain."""
        result = await self._evm_rpc(chain, "eth_blockNumber", [])
        if isinstance(result, str) and result.startswith("0x"):
            return int(result, 16)
        return 0

    async def _get_eth_balance(self, chain: str, address: str) -> float:
        """Get native token balance."""
        result = await self._evm_rpc(chain, "eth_getBalance", [address, "latest"])
        if isinstance(result, str) and result.startswith("0x"):
            return int(result, 16) / 1e18
        return 0.0

    async def _get_transfer_logs(self, chain: str, address: str, from_block: int, to_block: int, direction: str = "to") -> list:
        """Get ERC-20 Transfer events for a wallet."""
        # Normalize address to 32 bytes padded
        padded = "0x" + address[2:].lower().zfill(64)

        if direction == "to":
            topics = [TRANSFER_TOPIC, None, padded]
        else:
            topics = [TRANSFER_TOPIC, padded, None]

        hex_from = hex(from_block)
        hex_to = hex(to_block)

        result = await self._evm_rpc(chain, "eth_getLogs", [{
            "fromBlock": hex_from,
            "toBlock": hex_to,
            "topics": topics,
        }])

        if isinstance(result, list):
            return result
        return []

    async def _get_transaction_receipt(self, chain: str, tx_hash: str) -> dict:
        """Get transaction receipt."""
        return await self._evm_rpc(chain, "eth_getTransactionReceipt", [tx_hash])

    # === DexScreener API ===

    async def _dexscreener_token(self, token_address: str) -> dict:
        """Get token data from DexScreener."""
        session = await self._get_session()
        try:
            async with session.get(f"{DEXSCREENER_API}/tokens/{token_address}") as resp:
                data = await resp.json()
                pairs = data.get("pairs", [])
                if pairs:
                    # Return the most liquid pair
                    return max(pairs, key=lambda p: float(p.get("liquidity", {}).get("usd", 0) or 0))
                return {}
        except Exception:
            return {}

    async def _dexscreener_wallet(self, chain: str, address: str) -> list:
        """Get recent trades for a wallet from DexScreener (if available)."""
        session = await self._get_session()
        try:
            # DexScreener has a profiles endpoint that sometimes includes wallet data
            # But primarily we'll use on-chain RPC for wallet trades
            async with session.get(f"https://api.dexscreener.com/latest/dex/wallets/{address}") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("pairs", [])
                return []
        except Exception:
            return []

    # === TRADE DETECTION ===

    async def get_wallet_trades(self, address: str, chains: list = None, limit: int = 20) -> list:
        """
        Get recent trades for a wallet.
        Uses Etherscan-compatible APIs (free, reliable) with RPC fallback.
        """
        if chains is None:
            chains = ["bsc", "eth"]

        all_trades = []

        for chain in chains:
            if chain == "solana":
                sol_trades = await self._get_solana_trades(address, limit)
                all_trades.extend(sol_trades)
                continue

            try:
                # Primary: Use Etherscan-compatible API (needs API key for V2)
                trades = await self._get_explorer_trades(chain, address, limit)
                if trades:
                    all_trades.extend(trades)
                    continue

                # Fallback: RPC eth_getLogs (moderate range)
                trades = await self._get_rpc_trades(chain, address, limit)
                all_trades.extend(trades)
            except Exception as e:
                print(f"Error scanning {chain}: {e}")
                continue

        all_trades.sort(key=lambda t: t.timestamp, reverse=True)
        return all_trades[:limit]

    async def _get_explorer_trades(self, chain: str, address: str, limit: int = 20) -> list:
        """Get trades using Etherscan V2 API (needs API key)."""
        from explorer_keys import get_explorer_key, has_explorer_key
        
        if not has_explorer_key(chain):
            return []
        
        chain_id = CHAIN_IDS.get(chain)
        if not chain_id:
            return []
        
        api_key = get_explorer_key(chain)
        session = await self._get_session()
        trades = []

        try:
            params = {
                "chainid": chain_id,
                "module": "account",
                "action": "tokentx",
                "address": address,
                "page": 1,
                "offset": min(limit * 2, 50),
                "sort": "desc",
                "apikey": api_key,
            }
            async with session.get(ETHERSCAN_V2_API, params=params) as resp:
                data = await resp.json()

            if data.get("status") != "1" or not data.get("result"):
                return []

            seen_txs = set()
            for tx in data["result"][:limit * 2]:
                tx_hash = tx.get("hash", "")
                if tx_hash in seen_txs:
                    continue
                seen_txs.add(tx_hash)

                token_addr = tx.get("contractAddress", "")
                token_symbol = tx.get("tokenSymbol", "???")
                token_name = tx.get("tokenName", "Unknown")
                decimals = int(tx.get("tokenDecimal", 18))
                value_raw = int(tx.get("value", 0))
                value = value_raw / (10 ** decimals) if decimals > 0 else value_raw

                # Determine buy/sell: if 'to' is wallet → buy, if 'from' is wallet → sell
                is_buy = tx.get("to", "").lower() == address.lower()
                action = "buy" if is_buy else "sell"

                # Skip native token wraps
                if token_addr.lower() == WRAPPED_NATIVE.get(chain, "").lower():
                    continue

                # Get price from DexScreener (cached)
                token_info = await self._dexscreener_token(token_addr)
                price_usd = float(token_info.get("priceUsd", 0) or 0)
                amount_usd = value * price_usd

                timestamp = int(tx.get("timeStamp", int(time.time())))

                trades.append(Trade(
                    tx_hash=tx_hash,
                    chain=chain,
                    timestamp=timestamp,
                    action=action,
                    token_address=token_addr,
                    token_symbol=token_symbol,
                    token_name=token_name,
                    amount=value,
                    amount_usd=amount_usd,
                    price_usd=price_usd,
                    dex=token_info.get("dexId", "unknown"),
                    pair_address=token_info.get("pairAddress", ""),
                ))

                if len(trades) >= limit:
                    break

            return trades

        except Exception as e:
            print(f"Explorer API error ({chain}): {e}")
            return []

    async def _get_rpc_trades(self, chain: str, address: str, limit: int = 20) -> list:
        """Fallback: get trades via RPC eth_getLogs (moderate block range)."""
        try:
            latest_block = await self._get_latest_block(chain)
            if latest_block <= 0:
                return []

            # Moderate range: ~2000 blocks (~2 hours on BSC, ~6 hours on ETH)
            from_block = max(0, latest_block - 2000)

            out_logs = await self._get_transfer_logs(chain, address, from_block, latest_block, "from")
            in_logs = await self._get_transfer_logs(chain, address, from_block, latest_block, "to")

            if not in_logs and not out_logs:
                return []

            return await self._process_evm_logs(chain, address, in_logs, out_logs)
        except Exception as e:
            print(f"RPC fallback error ({chain}): {e}")
            return []

    async def _process_evm_logs(self, chain: str, wallet: str, in_logs: list, out_logs: list) -> list:
        """Process raw transfer logs into structured trades."""
        trades = []
        seen_txs = set()

        # Process incoming (buys)
        for log in in_logs:
            tx_hash = log.get("transactionHash", "")
            if tx_hash in seen_txs:
                continue
            seen_txs.add(tx_hash)

            token_addr = log.get("address", "")
            if token_addr.lower() == WRAPPED_NATIVE.get(chain, "").lower():
                continue  # Skip native token wraps

            value_hex = log.get("data", "0x0")
            try:
                value = int(value_hex, 16) / 1e18  # Assuming 18 decimals (most ERC20)
            except:
                value = 0

            # Get token info from DexScreener
            token_info = await self._dexscreener_token(token_addr)
            token_symbol = token_info.get("baseToken", {}).get("symbol", "???")
            token_name = token_info.get("baseToken", {}).get("name", "Unknown")
            price_usd = float(token_info.get("priceUsd", 0) or 0)
            amount_usd = value * price_usd

            trades.append(Trade(
                tx_hash=tx_hash,
                chain=chain,
                timestamp=int(log.get("timeStamp", int(time.time())) if "timeStamp" in log else int(time.time())),
                action="buy",
                token_address=token_addr,
                token_symbol=token_symbol,
                token_name=token_name,
                amount=value,
                amount_usd=amount_usd,
                price_usd=price_usd,
                dex=token_info.get("dexId", "unknown"),
                pair_address=token_info.get("pairAddress", ""),
            ))

        # Process outgoing (sells)
        for log in out_logs:
            tx_hash = log.get("transactionHash", "")
            if tx_hash in seen_txs:
                continue
            seen_txs.add(tx_hash)

            token_addr = log.get("address", "")
            if token_addr.lower() == WRAPPED_NATIVE.get(chain, "").lower():
                continue

            value_hex = log.get("data", "0x0")
            try:
                value = int(value_hex, 16) / 1e18
            except:
                value = 0

            token_info = await self._dexscreener_token(token_addr)
            token_symbol = token_info.get("baseToken", {}).get("symbol", "???")
            token_name = token_info.get("baseToken", {}).get("name", "Unknown")
            price_usd = float(token_info.get("priceUsd", 0) or 0)
            amount_usd = value * price_usd

            trades.append(Trade(
                tx_hash=tx_hash,
                chain=chain,
                timestamp=int(time.time()),
                action="sell",
                token_address=token_addr,
                token_symbol=token_symbol,
                token_name=token_name,
                amount=value,
                amount_usd=amount_usd,
                price_usd=price_usd,
                dex=token_info.get("dexId", "unknown"),
                pair_address=token_info.get("pairAddress", ""),
            ))

        return trades

    # === SOLANA ===

    async def _get_solana_trades(self, address: str, limit: int = 20) -> list:
        """Get recent Solana trades for a wallet."""
        session = await self._get_session()
        url = RPC_ENDPOINTS["solana"]
        trades = []

        try:
            # Get recent signatures
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getSignaturesForAddress",
                "params": [address, {"limit": limit}]
            }
            async with session.post(url, json=payload) as resp:
                data = await resp.json()
                signatures = data.get("result", [])

            for sig_info in signatures[:limit]:
                sig = sig_info.get("signature", "")
                slot = sig_info.get("slot", 0)

                # Get transaction details
                tx_payload = {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "getTransaction",
                    "params": [sig, {"encoding": "json", "maxSupportedTransactionVersion": 0}]
                }
                async with session.post(url, json=tx_payload) as tx_resp:
                    tx_data = await tx_resp.json()
                    tx = tx_data.get("result")

                if not tx or not tx.get("meta"):
                    continue

                # Parse token transfers from transaction
                meta = tx.get("meta", {})
                pre_balances = meta.get("preTokenBalances", [])
                post_balances = meta.get("postTokenBalances", [])

                # Find token changes for our wallet
                for post in post_balances:
                    if post.get("owner") != address:
                        continue
                    mint = post.get("mint", "")
                    post_amount = float(post.get("uiTokenAmount", {}).get("uiAmount", 0) or 0)

                    # Find matching pre balance
                    pre_amount = 0
                    for pre in pre_balances:
                        if pre.get("mint") == mint and pre.get("owner") == address:
                            pre_amount = float(pre.get("uiTokenAmount", {}).get("uiAmount", 0) or 0)
                            break

                    diff = post_amount - pre_amount
                    if abs(diff) < 0.000001:
                        continue

                    action = "buy" if diff > 0 else "sell"
                    amount = abs(diff)

                    # Get token info from DexScreener
                    token_info = await self._dexscreener_token(mint)
                    symbol = token_info.get("baseToken", {}).get("symbol", "???")
                    name = token_info.get("baseToken", {}).get("name", "Unknown")
                    price = float(token_info.get("priceUsd", 0) or 0)

                    trades.append(Trade(
                        tx_hash=sig,
                        chain="solana",
                        timestamp=tx.get("blockTime", int(time.time())),
                        action=action,
                        token_address=mint,
                        token_symbol=symbol,
                        token_name=name,
                        amount=amount,
                        amount_usd=amount * price,
                        price_usd=price,
                        dex=token_info.get("dexId", "unknown"),
                        pair_address=token_info.get("pairAddress", ""),
                    ))

        except Exception as e:
            print(f"Solana error: {e}")

        return trades

    # === PnL CALCULATION ===

    async def calculate_pnl(self, address: str, chains: list = None) -> WalletPnL:
        """
        Calculate PnL for a wallet by analyzing trade history.
        Matches buys and sells for each token to compute realized PnL.
        """
        trades = await self.get_wallet_trades(address, chains, limit=50)

        if not trades:
            return WalletPnL(
                total_trades=0, winning_trades=0, losing_trades=0,
                win_rate=0, total_realized_pnl=0, total_unrealized_pnl=0,
                total_pnl=0
            )

        # Group trades by token
        token_trades = {}
        for trade in trades:
            key = f"{trade.chain}:{trade.token_address}"
            if key not in token_trades:
                token_trades[key] = []
            token_trades[key].append(trade)

        total_realized = 0.0
        winning = 0
        losing = 0
        best_trade = None
        worst_trade = None
        hold_times = []

        for token_key, token_txs in token_trades.items():
            buys = [t for t in token_txs if t.action == "buy"]
            sells = [t for t in token_txs if t.action == "sell"]

            # Simple PnL: match earliest buy with earliest sell
            for buy, sell in zip(buys, sells):
                pnl = sell.amount_usd - buy.amount_usd
                total_realized += pnl

                if pnl > 0:
                    winning += 1
                else:
                    losing += 1

                if best_trade is None or pnl > (best_trade.amount_usd if best_trade else 0):
                    best_trade = buy
                if worst_trade is None or pnl < (worst_trade.amount_usd if worst_trade else 0):
                    worst_trade = buy

                # Hold time
                hold_time = (sell.timestamp - buy.timestamp) / 3600
                if hold_time > 0:
                    hold_times.append(hold_time)

        total_trades = winning + losing
        win_rate = (winning / total_trades * 100) if total_trades > 0 else 0
        avg_hold = sum(hold_times) / len(hold_times) if hold_times else 0

        return WalletPnL(
            total_trades=total_trades,
            winning_trades=winning,
            losing_trades=losing,
            win_rate=round(win_rate, 1),
            total_realized_pnl=round(total_realized, 2),
            total_unrealized_pnl=0,  # Would need current holdings
            total_pnl=round(total_realized, 2),
            best_trade=best_trade,
            worst_trade=worst_trade,
            avg_hold_time_hours=round(avg_hold, 1),
        )

    # === WALLET SUMMARY ===

    async def get_wallet_summary(self, address: str, chains: list = None, is_pro: bool = False) -> dict:
        """
        Get full wallet summary: trades, PnL, holdings.
        Free tier: limited trades, no PnL.
        Pro tier: full data.
        """
        if chains is None:
            chains = ["bsc", "eth"]

        # Always get some trades
        trades = await self.get_wallet_trades(address, chains, limit=50)

        # Free tier: only show 3 trades, no PnL
        if not is_pro:
            display_trades = trades[:3]
            trade_data = [{
                "tx_hash": t.tx_hash[:10] + "...",
                "chain": t.chain,
                "action": t.action,
                "token": t.token_symbol,
                "amount": round(t.amount, 4),
                "locked": True,
            } for t in display_trades]

            return {
                "address": address,
                "chains": chains,
                "plan": "free",
                "recent_trades": trade_data,
                "total_trades_visible": 3,
                "total_trades_hidden": max(0, len(trades) - 3),
                "pnl": None,
                "holdings": None,
                "upgrade_message": "Upgrade to Pro to see full trade history, PnL breakdown, and holdings."
            }

        # Pro tier: full data
        pnl = await self.calculate_pnl(address, chains)

        trade_data = [{
            "tx_hash": t.tx_hash,
            "chain": t.chain,
            "timestamp": t.timestamp,
            "action": t.action,
            "token_address": t.token_address,
            "token_symbol": t.token_symbol,
            "token_name": t.token_name,
            "amount": round(t.amount, 6),
            "amount_usd": round(t.amount_usd, 2),
            "price_usd": round(t.price_usd, 8),
            "dex": t.dex,
        } for t in trades]

        return {
            "address": address,
            "chains": chains,
            "plan": "pro",
            "recent_trades": trade_data,
            "total_trades": len(trades),
            "pnl": {
                "total_trades": pnl.total_trades,
                "winning_trades": pnl.winning_trades,
                "losing_trades": pnl.losing_trades,
                "win_rate": pnl.win_rate,
                "total_realized_pnl": pnl.total_realized_pnl,
                "total_pnl": pnl.total_pnl,
                "avg_hold_time_hours": pnl.avg_hold_time_hours,
            },
            "holdings": [],  # TODO: implement holdings
        }
