"""
Chain Sentinel — FastAPI Backend
Token Safety Scanner — Multi-chain
"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from scanner import TokenScanner
from wallet_tracker import WalletTracker
from launchpad_scanner import LaunchpadScanner
from pydantic import BaseModel
from typing import Optional
from collections import defaultdict
import time
import os
import hmac
import hashlib
import json as json_module
from api_keys import api_key_manager

app = FastAPI(
    title="Chain Sentinel",
    description="Token Safety Scanner — Multi-chain",
    version="0.5.0",
    docs_url=None,
    redoc_url=None
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

scanner = TokenScanner()
wallet_tracker = WalletTracker()
launchpad_scanner = LaunchpadScanner()

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")


# === RATE LIMITER ===
class RateLimiter:
    def __init__(self, max_requests: int = 20, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window = window_seconds
        self.requests = defaultdict(list)
    
    def is_allowed(self, client_ip: str) -> bool:
        now = time.time()
        self.requests[client_ip] = [
            t for t in self.requests[client_ip] 
            if now - t < self.window
        ]
        if len(self.requests[client_ip]) >= self.max_requests:
            return False
        self.requests[client_ip].append(now)
        return True
    
    def get_remaining(self, client_ip: str) -> int:
        now = time.time()
        self.requests[client_ip] = [
            t for t in self.requests[client_ip]
            if now - t < self.window
        ]
        return max(0, self.max_requests - len(self.requests[client_ip]))
    
    def get_reset_time(self, client_ip: str) -> int:
        if not self.requests[client_ip]:
            return 0
        oldest = min(self.requests[client_ip])
        return max(0, int(self.window - (time.time() - oldest)))

rate_limiter = RateLimiter(max_requests=20, window_seconds=60)


# === RATE LIMIT MIDDLEWARE ===
@app.middleware("http")
async def add_rate_limit_headers(request: Request, call_next):
    """Add X-RateLimit-* headers to all /api/ responses."""
    response = await call_next(request)
    
    if request.url.path.startswith("/api/"):
        client_ip = request.client.host
        remaining = rate_limiter.get_remaining(client_ip)
        reset_time = rate_limiter.get_reset_time(client_ip)
        
        # Determine max based on API key
        api_key = request.headers.get("X-API-Key")
        max_req = 20  # default free
        if api_key:
            key_info = api_key_manager.validate_key(api_key)
            if key_info:
                limits = api_key_manager.get_usage_limits(key_info["plan"])
                max_req = limits.get("scans_per_minute", 20)
                if max_req == -1:
                    max_req = 999999  # unlimited
        
        response.headers["X-RateLimit-Limit"] = str(max_req)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int(time.time()) + reset_time)
        response.headers["X-RateLimit-Policy"] = f"{max_req};w=60"
    
    return response


# === WEBHOOK SYSTEM ===
WEBHOOKS_FILE = os.path.join(os.path.dirname(__file__), "webhooks.json")

def _load_webhooks() -> dict:
    if os.path.exists(WEBHOOKS_FILE):
        with open(WEBHOOKS_FILE) as f:
            return json_module.load(f)
    return {"subscriptions": []}

def _save_webhooks(data: dict):
    with open(WEBHOOKS_FILE, "w") as f:
        json_module.dump(data, f, indent=2)

def _generate_webhook_secret() -> str:
    import secrets
    return f"whsec_{secrets.token_urlsafe(32)}"

def _sign_payload(payload: str, secret: str) -> str:
    """Generate HMAC-SHA256 signature for webhook payload."""
    return hmac.new(
        secret.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()


class WebhookSubscribe(BaseModel):
    url: str
    events: list = ["scan.complete"]
    description: str = ""


class WebhookResponse(BaseModel):
    id: str
    url: str
    events: list
    secret: str
    active: bool
    created_at: str


# === MODELS ===
class ScanRequest(BaseModel):
    address: str
    chain: str = "bsc"


class ScanResponse(BaseModel):
    address: str
    chain: str
    name: str
    symbol: str
    
    safety_score: int
    risk_level: str
    
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
    
    data_sources: list = []
    warnings: list = []
    positives: list = []


class ContactRequest(BaseModel):
    name: str
    email: str
    subject: str
    message: str


# === ROUTES ===
@app.get("/", response_class=HTMLResponse)
async def root():
    with open("static/index.html", "r") as f:
        return HTMLResponse(content=f.read())


@app.get("/docs", response_class=HTMLResponse)
@app.get("/api-docs", response_class=HTMLResponse)
async def api_docs():
    with open("static/docs.html", "r") as f:
        return HTMLResponse(content=f.read())


@app.post("/api/scan", response_model=ScanResponse)
async def scan_token(req: ScanRequest, request: Request):
    # Check for API key in headers
    api_key = request.headers.get("X-API-Key")
    user_plan = "free"
    
    if api_key:
        key_info = api_key_manager.validate_key(api_key)
        if key_info:
            user_plan = key_info.get("plan", "free")
            # Get limits for user's plan
            limits = api_key_manager.get_usage_limits(user_plan)
            max_requests = limits["scans_per_minute"]
        else:
            # Invalid API key, fall back to free tier
            max_requests = 20
    else:
        # No API key, use free tier
        max_requests = 20
    
    # Rate limit check
    client_ip = request.client.host
    if not rate_limiter.is_allowed(client_ip):
        remaining_time = rate_limiter.get_reset_time(client_ip)
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Try again in {remaining_time}s. ({max_requests} scans/min limit)"
        )
    
    report = await scanner.scan_token(req.address, req.chain)
    
    return ScanResponse(
        address=report.address,
        chain=report.chain,
        name=report.name,
        symbol=report.symbol,
        
        safety_score=report.safety_score,
        risk_level=report.risk_level,
        
        is_honeypot=report.is_honeypot,
        can_sell=report.can_sell,
        buy_tax=report.buy_tax,
        sell_tax=report.sell_tax,
        
        owner_renounced=report.owner_renounced,
        owner_address=report.owner_address,
        
        is_verified=report.is_verified,
        is_proxy=report.is_proxy,
        
        liquidity_locked=report.liquidity_locked,
        lock_platform=report.lock_platform,
        
        price_usd=report.price_usd,
        volume_24h=report.volume_24h,
        market_cap=report.market_cap,
        holders=report.holders,
        
        data_sources=report.data_sources,
        warnings=report.warnings,
        positives=report.positives,
    )


@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "chain-sentinel", "version": "0.5.0"}



@app.post("/api/keys/generate")
async def generate_api_key(request: Request):
    """Generate a new API key (requires authentication)"""
    # In production, this would require proper authentication
    # For now, we'll use a simple demo endpoint
    data = await request.json()
    user_id = data.get("user_id", "demo_user")
    plan = data.get("plan", "pro")
    
    if plan not in ["free", "pro", "enterprise"]:
        raise HTTPException(status_code=400, detail="Invalid plan")
    
    key = api_key_manager.generate_key(user_id, plan)
    limits = api_key_manager.get_usage_limits(plan)
    
    return {
        "api_key": key,
        "plan": plan,
        "limits": limits,
        "message": "Keep this key safe. It won't be shown again."
    }


@app.get("/api/keys/validate")
async def validate_api_key(request: Request):
    """Validate an API key"""
    api_key = request.headers.get("X-API-Key")
    
    if not api_key:
        raise HTTPException(status_code=400, detail="X-API-Key header required")
    
    key_info = api_key_manager.validate_key(api_key)
    
    if not key_info:
        raise HTTPException(status_code=401, detail="Invalid or inactive API key")
    
    limits = api_key_manager.get_usage_limits(key_info["plan"])
    
    return {
        "valid": True,
        "plan": key_info["plan"],
        "usage_count": key_info["usage_count"],
        "limits": limits
    }


@app.get("/api/plans")
async def get_plans():
    """Get available plans and their limits"""
    return {
        "plans": [
            {
                "name": "Free",
                "price": 0,
                "currency": "USD",
                "interval": "forever",
                "features": [
                    "20 scans per minute",
                    "Basic safety report",
                    "9 blockchain networks",
                    "Honeypot detection"
                ],
                "limits": api_key_manager.get_usage_limits("free")
            },
            {
                "name": "Pro",
                "price": 5,
                "currency": "USD",
                "interval": "month",
                "features": [
                    "Unlimited scans",
                    "Advanced safety report",
                    "API access (1000 calls/day)",
                    "Wallet monitoring (5 wallets)",
                    "Email alerts",
                    "Priority support"
                ],
                "limits": api_key_manager.get_usage_limits("pro")
            },
            {
                "name": "Enterprise",
                "price": 25,
                "currency": "USD",
                "interval": "month",
                "features": [
                    "Everything in Pro",
                    "Unlimited API calls",
                    "Wallet monitoring (50 wallets)",
                    "Custom integrations",
                    "White-label option",
                    "Dedicated support"
                ],
                "limits": api_key_manager.get_usage_limits("enterprise")
            }
        ]
    }


# === WEBHOOK ENDPOINTS ===
@app.post("/api/webhooks", response_model=WebhookResponse)
async def create_webhook(req: WebhookSubscribe, request: Request):
    """Subscribe to webhook events. Pro/Enterprise only."""
    api_key = request.headers.get("X-API-Key")
    if not api_key:
        raise HTTPException(status_code=401, detail="API key required for webhooks")
    
    key_info = api_key_manager.validate_key(api_key)
    if not key_info or key_info["plan"] == "free":
        raise HTTPException(status_code=403, detail="Webhooks require Pro or Enterprise plan")
    
    # Validate URL
    if not req.url.startswith("https://"):
        raise HTTPException(status_code=400, detail="Webhook URL must use HTTPS")
    
    # Validate events
    valid_events = ["scan.complete", "scan.risk_high", "scan.honeypot", "key.expired"]
    invalid = [e for e in req.events if e not in valid_events]
    if invalid:
        raise HTTPException(status_code=400, detail=f"Invalid events: {invalid}. Valid: {valid_events}")
    
    import uuid
    webhook_id = f"wh_{uuid.uuid4().hex[:16]}"
    secret = _generate_webhook_secret()
    
    webhooks = _load_webhooks()
    webhook_entry = {
        "id": webhook_id,
        "url": req.url,
        "events": req.events,
        "secret": secret,
        "active": True,
        "api_key": api_key,
        "description": req.description,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "delivery_count": 0,
        "last_delivery": None
    }
    webhooks["subscriptions"].append(webhook_entry)
    _save_webhooks(webhooks)
    
    return WebhookResponse(
        id=webhook_id,
        url=req.url,
        events=req.events,
        secret=secret,
        active=True,
        created_at=webhook_entry["created_at"]
    )


@app.get("/api/webhooks")
async def list_webhooks(request: Request):
    """List your webhook subscriptions."""
    api_key = request.headers.get("X-API-Key")
    if not api_key:
        raise HTTPException(status_code=401, detail="API key required")
    
    webhooks = _load_webhooks()
    user_hooks = [
        {
            "id": w["id"],
            "url": w["url"],
            "events": w["events"],
            "active": w["active"],
            "description": w.get("description", ""),
            "created_at": w["created_at"],
            "delivery_count": w.get("delivery_count", 0),
            "last_delivery": w.get("last_delivery")
        }
        for w in webhooks["subscriptions"]
        if w.get("api_key") == api_key
    ]
    
    return {"webhooks": user_hooks}


@app.delete("/api/webhooks/{webhook_id}")
async def delete_webhook(webhook_id: str, request: Request):
    """Delete a webhook subscription."""
    api_key = request.headers.get("X-API-Key")
    if not api_key:
        raise HTTPException(status_code=401, detail="API key required")
    
    webhooks = _load_webhooks()
    original_count = len(webhooks["subscriptions"])
    webhooks["subscriptions"] = [
        w for w in webhooks["subscriptions"]
        if not (w["id"] == webhook_id and w.get("api_key") == api_key)
    ]
    
    if len(webhooks["subscriptions"]) == original_count:
        raise HTTPException(status_code=404, detail="Webhook not found")
    
    _save_webhooks(webhooks)
    return {"status": "deleted", "id": webhook_id}


@app.post("/api/webhooks/{webhook_id}/test")
async def test_webhook(webhook_id: str, request: Request):
    """Send a test payload to your webhook URL."""
    import urllib.request
    
    api_key = request.headers.get("X-API-Key")
    if not api_key:
        raise HTTPException(status_code=401, detail="API key required")
    
    webhooks = _load_webhooks()
    webhook = None
    for w in webhooks["subscriptions"]:
        if w["id"] == webhook_id and w.get("api_key") == api_key:
            webhook = w
            break
    
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")
    
    # Build test payload
    test_payload = json_module.dumps({
        "event": "webhook.test",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "data": {
            "message": "This is a test webhook delivery from Chain Sentinel",
            "webhook_id": webhook_id
        }
    })
    
    signature = _sign_payload(test_payload, webhook["secret"])
    
    try:
        req = urllib.request.Request(
            webhook["url"],
            data=test_payload.encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "X-ChainSentinel-Signature": f"sha256={signature}",
                "X-ChainSentinel-Event": "webhook.test",
                "X-ChainSentinel-Delivery": f"test_{int(time.time())}",
                "User-Agent": "ChainSentinel-Webhook/1.0"
            },
            method="POST"
        )
        resp = urllib.request.urlopen(req, timeout=10)
        status_code = resp.getcode()
        
        # Update delivery count
        webhook["delivery_count"] = webhook.get("delivery_count", 0) + 1
        webhook["last_delivery"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        _save_webhooks(webhooks)
        
        return {
            "status": "delivered",
            "http_status": status_code,
            "signature": f"sha256={signature}"
        }
    except Exception as e:
        return {
            "status": "failed",
            "error": str(e),
            "signature": f"sha256={signature}"
        }


# === CHANGELOG PAGE ===
@app.get("/changelog", response_class=HTMLResponse)
async def changelog():
    with open("static/changelog.html", "r") as f:
        return HTMLResponse(content=f.read())



# === v0.5.0 — SMART WALLET & LAUNCHPAD ENDPOINTS ===

class WalletRequest(BaseModel):
    address: str
    chains: list = ["bsc", "eth"]

class LaunchpadRequest(BaseModel):
    launchpads: list = ["dexscreener"]
    chains: list = []
    limit: int = 10


@app.post("/api/v1/wallet/trades")
async def wallet_trades(req: WalletRequest, request: Request):
    """Get recent trades for a wallet. Free: 3 trades. Pro: unlimited."""
    api_key = request.headers.get("X-API-Key")
    is_pro = False
    if api_key:
        key_info = api_key_manager.validate_key(api_key)
        if key_info and key_info.get("plan") in ("pro", "enterprise"):
            is_pro = True

    trades = await wallet_tracker.get_wallet_trades(req.address, req.chains, limit=50)

    if not is_pro:
        # Free: only 3 trades, limited data
        return {
            "address": req.address,
            "plan": "free",
            "trades": [{
                "tx_hash": t.tx_hash[:10] + "...",
                "chain": t.chain,
                "action": t.action,
                "token": t.token_symbol,
                "amount": round(t.amount, 4),
                "locked": True,
            } for t in trades[:3]],
            "total_visible": 3,
            "total_hidden": max(0, len(trades) - 3),
            "upgrade_message": "Upgrade to Pro to see full trade history, PnL, and all chains."
        }

    # Pro: full data
    return {
        "address": req.address,
        "plan": "pro",
        "trades": [{
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
        } for t in trades],
        "total": len(trades),
    }


@app.post("/api/v1/wallet/pnl")
async def wallet_pnl(req: WalletRequest, request: Request):
    """Get PnL for a wallet. Pro only."""
    api_key = request.headers.get("X-API-Key")
    is_pro = False
    if api_key:
        key_info = api_key_manager.validate_key(api_key)
        if key_info and key_info.get("plan") in ("pro", "enterprise"):
            is_pro = True

    if not is_pro:
        return {
            "address": req.address,
            "plan": "free",
            "pnl": None,
            "upgrade_message": "PnL breakdown is a Pro feature. Upgrade to see win rate, realized PnL, and trade analysis."
        }

    pnl = await wallet_tracker.calculate_pnl(req.address, req.chains)

    return {
        "address": req.address,
        "plan": "pro",
        "pnl": {
            "total_trades": pnl.total_trades,
            "winning_trades": pnl.winning_trades,
            "losing_trades": pnl.losing_trades,
            "win_rate": pnl.win_rate,
            "total_realized_pnl": pnl.total_realized_pnl,
            "total_pnl": pnl.total_pnl,
            "avg_hold_time_hours": pnl.avg_hold_time_hours,
        }
    }


@app.post("/api/v1/wallet/summary")
async def wallet_summary(req: WalletRequest, request: Request):
    """Get full wallet summary. Free: limited. Pro: full."""
    api_key = request.headers.get("X-API-Key")
    is_pro = False
    if api_key:
        key_info = api_key_manager.validate_key(api_key)
        if key_info and key_info.get("plan") in ("pro", "enterprise"):
            is_pro = True

    result = await wallet_tracker.get_wallet_summary(req.address, req.chains, is_pro=is_pro)
    return result


@app.post("/api/v1/launchpads/tokens")
async def launchpad_tokens(req: LaunchpadRequest, request: Request):
    """Get new tokens from launchpads. Free: 1 launchpad, 5 tokens. Pro: all, unlimited."""
    api_key = request.headers.get("X-API-Key")
    is_pro = False
    if api_key:
        key_info = api_key_manager.validate_key(api_key)
        if key_info and key_info.get("plan") in ("pro", "enterprise"):
            is_pro = True

    result = await launchpad_scanner.get_all_launchpad_tokens(
        launchpads=req.launchpads,
        chains=req.chains,
        limit_per_source=req.limit,
        is_pro=is_pro,
    )
    return result


@app.get("/api/v1/launchpads/trending")
async def launchpad_trending(request: Request):
    """Get trending tokens across all launchpads. Free: top 5. Pro: full list."""
    api_key = request.headers.get("X-API-Key")
    is_pro = False
    if api_key:
        key_info = api_key_manager.validate_key(api_key)
        if key_info and key_info.get("plan") in ("pro", "enterprise"):
            is_pro = True

    # Get boosted tokens (trending)
    boosted = await launchpad_scanner.get_dexscreener_boosted(limit=20)

    tokens = []
    for t in boosted:
        if is_pro:
            tokens.append({
                "address": t.address,
                "chain": t.chain,
                "launchpad": t.launchpad,
                "name": t.name,
                "symbol": t.symbol,
                "price_usd": round(t.price_usd, 8),
                "market_cap": round(t.market_cap, 2),
                "volume_24h": round(t.volume_24h, 2),
                "volume_1h": round(t.volume_1h, 2),
                "liquidity_usd": round(t.liquidity_usd, 2),
                "price_change_1h": t.price_change_1h,
                "price_change_24h": t.price_change_24h,
                "buy_count_24h": t.buy_count_24h,
                "sell_count_24h": t.sell_count_24h,
                "dex": t.dex,
            })
        else:
            tokens.append({
                "address": t.address[:8] + "...",
                "chain": t.chain,
                "name": t.name,
                "symbol": t.symbol,
                "price_usd": "***",
                "market_cap": "***",
                "locked": True,
            })

    return {
        "plan": "pro" if is_pro else "free",
        "tokens": tokens if is_pro else tokens[:5],
        "total": len(boosted),
        "upgrade_message": None if is_pro else "Upgrade to Pro to see prices, volume, and all trending tokens."
    }


@app.get("/api/v1/launchpads/pumpfun")
async def launchpad_pumpfun(request: Request):
    """Get new tokens from pump.fun. Pro only."""
    api_key = request.headers.get("X-API-Key")
    is_pro = False
    if api_key:
        key_info = api_key_manager.validate_key(api_key)
        if key_info and key_info.get("plan") in ("pro", "enterprise"):
            is_pro = True

    if not is_pro:
        return {
            "plan": "free",
            "launchpad": "pump.fun",
            "tokens": [],
            "upgrade_message": "pump.fun data is a Pro feature. Upgrade to see new tokens, bonding curve %, and early buyer data."
        }

    tokens = await launchpad_scanner.get_pumpfun_tokens(limit=20)
    return {
        "plan": "pro",
        "launchpad": "pump.fun",
        "tokens": [{
            "address": t.address,
            "chain": "solana",
            "name": t.name,
            "symbol": t.symbol,
            "price_usd": round(t.price_usd, 8),
            "market_cap": round(t.market_cap, 2),
            "holders": t.holders,
            "created_at": t.created_at,
            "bonding_curve_pct": t.bonding_curve_pct,
            "website": t.website,
            "twitter": t.twitter,
        } for t in tokens],
        "total": len(tokens),
    }


@app.get("/api/v1/launchpads/fourmeme")
async def launchpad_fourmeme(request: Request):
    """Get new tokens from four.meme. Pro only."""
    api_key = request.headers.get("X-API-Key")
    is_pro = False
    if api_key:
        key_info = api_key_manager.validate_key(api_key)
        if key_info and key_info.get("plan") in ("pro", "enterprise"):
            is_pro = True

    if not is_pro:
        return {
            "plan": "free",
            "launchpad": "four.meme",
            "tokens": [],
            "upgrade_message": "four.meme data is a Pro feature. Upgrade to see new BNB Chain launches."
        }

    tokens = await launchpad_scanner.get_fourmeme_tokens(limit=20)
    return {
        "plan": "pro",
        "launchpad": "four.meme",
        "tokens": [{
            "address": t.address,
            "chain": "bsc",
            "name": t.name,
            "symbol": t.symbol,
            "price_usd": round(t.price_usd, 8),
            "market_cap": round(t.market_cap, 2),
            "holders": t.holders,
            "created_at": t.created_at,
            "website": t.website,
            "twitter": t.twitter,
        } for t in tokens],
        "total": len(tokens),
    }


@app.get("/api/v1/launchpads/gmgn")
async def launchpad_gmgn(request: Request):
    """Get trending tokens from gmgn.ai. Pro only."""
    api_key = request.headers.get("X-API-Key")
    is_pro = False
    if api_key:
        key_info = api_key_manager.validate_key(api_key)
        if key_info and key_info.get("plan") in ("pro", "enterprise"):
            is_pro = True

    if not is_pro:
        return {
            "plan": "free",
            "launchpad": "gmgn",
            "tokens": [],
            "upgrade_message": "gmgn.ai data is a Pro feature. Upgrade to see smart money flows."
        }

    tokens = await launchpad_scanner.get_gmgn_trending(limit=20)
    return {
        "plan": "pro",
        "launchpad": "gmgn",
        "tokens": [{
            "address": t.address,
            "chain": "solana",
            "name": t.name,
            "symbol": t.symbol,
            "price_usd": round(t.price_usd, 8),
            "market_cap": round(t.market_cap, 2),
            "volume_1h": round(t.volume_1h, 2),
            "holders": t.holders,
            "price_change_1h": t.price_change_1h,
            "buy_count_24h": t.buy_count_24h,
            "sell_count_24h": t.sell_count_24h,
            "top_10_hold_pct": t.top_10_hold_pct,
        } for t in tokens],
        "total": len(tokens),
    }


@app.post("/api/contact")
async def contact(req: ContactRequest):
    """Contact form — forwards message to business email"""
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    
    # Build email
    msg = MIMEMultipart()
    msg["From"] = f"Chain Sentinel <noreply@chainshieldsentinel.tech>"
    msg["To"] = "info@chainshieldsentinel.tech"
    msg["Reply-To"] = req.email
    msg["Subject"] = f"[Chain Sentinel Contact] {req.subject}"
    
    body = f"""
    New contact form submission:
    
    Name: {req.name}
    Email: {req.email}
    Subject: {req.subject}
    
    Message:
    {req.message}
    """
    msg.attach(MIMEText(body, "plain"))
    
    # Send via SMTP (if configured)
    try:
        smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
        smtp_port = int(os.getenv("SMTP_PORT", "587"))
        smtp_user = os.getenv("SMTP_USER", "")
        smtp_pass = os.getenv("SMTP_PASS", "")
        
        if smtp_user and smtp_pass:
            with smtplib.SMTP(smtp_host, smtp_port) as server:
                server.starttls()
                server.login(smtp_user, smtp_pass)
                server.send_message(msg)
            return {"status": "ok", "message": "Message sent successfully"}
        else:
            # No SMTP configured — log and return success
            print(f"[CONTACT FORM] From: {req.email} | Subject: {req.subject}")
            print(f"[CONTACT FORM] Message: {req.message[:200]}")
            return {"status": "ok", "message": "Message received (email forwarding pending)"}
    except Exception as e:
        print(f"[CONTACT ERROR] {e}")
        return {"status": "ok", "message": "Message received"}


# For local development
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8888, reload=True)
