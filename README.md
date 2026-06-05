# 🛡️ Chain Sentinel

**Token Safety Scanner** — Detect honeypots, rugpulls, and scams across 9 blockchain networks.

## Features

- 🔍 **Token Safety Scanner** — Paste any contract address, get instant safety report
- 🍯 **Honeypot Detection** — Know if you can sell before you buy
- 📊 **Safety Score** — 0-100 rating with risk levels (LOW/MEDIUM/HIGH/CRITICAL)
- ⚡ **Rate Limiting** — 20 scans per minute (free tier)
- 🔗 **9 Chains Supported** — BSC, ETH, Base, Arbitrum, Polygon, Avalanche, Fantom, Optimism, Solana
- 📱 **Responsive UI** — Dark theme, mobile-friendly
- ⚠️ **Unknown Token Handling** — Shows "UNKNOWN" risk for tokens with insufficient data

## Pricing

| Plan | Price | Features |
|------|-------|----------|
| **Free** | $0/forever | 20 scans/min, basic report, 9 chains |
| **Pro** | $5/month | Unlimited scans, API access, wallet monitoring |
| **Enterprise** | $25/month | Everything in Pro + unlimited API + white-label |

## Tech Stack

- **Backend:** Python FastAPI
- **Frontend:** HTML + Tailwind CSS
- **APIs:** GoPlus Security + DexScreener (free, no keys needed)
- **Solana:** Direct RPC calls for on-chain data

## Quick Start

```bash
# Clone
git clone https://github.com/0xairdropnoob/chain-shield.git
cd chain-shield

# Setup
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Run
python3 app.py
```

Visit `http://localhost:8888`

## API Documentation

### Authentication

Include your API key in the request headers:

```
X-API-Key: your_api_key_here
```

### POST `/api/scan`

```json
{
  "address": "0x0E09FaBB73Bd3Ade0a17ECC321fD13a19e81cE82",
  "chain": "bsc"
}
```

**Response:**
```json
{
  "address": "0x0E09FaBB73Bd3Ade0a17ECC321fD13a19e81cE82",
  "chain": "bsc",
  "name": "PancakeSwap Token",
  "symbol": "Cake",
  "safety_score": 100,
  "risk_level": "LOW",
  "is_honeypot": false,
  "can_sell": true,
  "owner_renounced": true,
  "is_verified": true,
  "warnings": [],
  "positives": ["✅ Owner has renounced ownership", "..."]
}
```

### POST `/api/keys/generate`

Generate a new API key:

```json
{
  "user_id": "user123",
  "plan": "pro"
}
```

### GET `/api/keys/validate`

Validate an API key:

```
GET /api/keys/validate
X-API-Key: your_api_key_here
```

### GET `/api/plans`

Get available plans and their limits.

## Supported Chains

| Chain | Chain ID |
|-------|----------|
| 🟡 BNB Smart Chain | `bsc` |
| 🔷 Ethereum | `eth` |
| 🔵 Base | `base` |
| 🌀 Arbitrum | `arbitrum` |
| 🟣 Polygon | `polygon` |
| 🔴 Avalanche | `avalanche` |
| 👻 Fantom | `fantom` |
| 🔴 Optimism | `optimism` |
| 🟣 Solana | `solana` |

## Deployment

### Vercel (Recommended)

1. Install Vercel CLI:
   ```bash
   npm install -g vercel
   ```

2. Deploy:
   ```bash
   vercel --prod
   ```

3. Configure your domain in Vercel dashboard.

### Manual Deployment

1. Build the application:
   ```bash
   pip install -r requirements.txt
   ```

2. Run with uvicorn:
   ```bash
   uvicorn app:app --host 0.0.0.0 --port 8888
   ```

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `SMTP_HOST` | SMTP server for contact form | No |
| `SMTP_PORT` | SMTP port | No |
| `SMTP_USER` | SMTP username | No |
| `SMTP_PASS` | SMTP password | No |

## Roadmap

- [x] Token safety scanner
- [x] Honeypot detection
- [x] Multi-chain support
- [x] API key system
- [x] Pricing tiers
- [ ] Wallet monitoring
- [ ] Historical scan data
- [ ] Browser extension
- [ ] Telegram bot

## License

MIT

---

**Part of the [Sentinel](https://github.com/0xairdropnoob) Suite**
