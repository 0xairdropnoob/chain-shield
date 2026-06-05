"""
Chain Sentinel — FastAPI Backend
Token Safety Scanner — Multi-chain
"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from scanner import TokenScanner
from pydantic import BaseModel
from typing import Optional
from collections import defaultdict
import time
import os
from api_keys import api_key_manager

app = FastAPI(
    title="Chain Sentinel",
    description="Token Safety Scanner — Multi-chain",
    version="0.3.0"
)

scanner = TokenScanner()

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
    return {"status": "ok", "service": "chain-sentinel", "version": "0.3.0"}



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
