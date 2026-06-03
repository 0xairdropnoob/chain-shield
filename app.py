"""
Chain Shield — FastAPI Backend
Sentinel's Token Safety Scanner — Multi-chain
"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from scanner import TokenScanner
from pydantic import BaseModel
from typing import Optional
from collections import defaultdict
import time
import uvicorn

app = FastAPI(
    title="Chain Shield",
    description="Sentinel's Token Safety Scanner",
    version="0.2.0"
)

scanner = TokenScanner()


# === RATE LIMITER ===
# Simple in-memory rate limiter: 20 scans per minute per IP
class RateLimiter:
    def __init__(self, max_requests: int = 20, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window = window_seconds
        self.requests = defaultdict(list)
    
    def is_allowed(self, client_ip: str) -> bool:
        now = time.time()
        # Clean old requests
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


# === ROUTES ===
@app.get("/", response_class=HTMLResponse)
async def root():
    with open("static/index.html", "r") as f:
        return HTMLResponse(content=f.read())


@app.post("/api/scan", response_model=ScanResponse)
async def scan_token(req: ScanRequest, request: Request):
    # Rate limit check
    client_ip = request.client.host
    if not rate_limiter.is_allowed(client_ip):
        remaining_time = rate_limiter.get_reset_time(client_ip)
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Try again in {remaining_time}s. (20 scans/min limit)"
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
    return {"status": "ok", "service": "chain-shield", "version": "0.2.0"}


if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8888, reload=True)
