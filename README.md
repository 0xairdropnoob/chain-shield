# 🛡️ Chain Shield — Sentinel

**Token Safety Scanner** — Detect honeypots, rugpulls, and scams across 9 blockchain networks.

## Features

- 🔍 **Token Safety Scanner** — Paste any contract address, get instant safety report
- 🍯 **Honeypot Detection** — Know if you can sell before you buy
- 📊 **Safety Score** — 0-100 rating with risk levels (LOW/MEDIUM/HIGH/CRITICAL)
- ⚡ **Rate Limiting** — 20 scans per minute (free tier)
- 🔗 **9 Chains Supported** — BSC, ETH, Base, Arbitrum, Polygon, Avalanche, Fantom, Optimism, Solana
- 📱 **Responsive UI** — Dark theme, mobile-friendly
- ⚠️ **Unknown Token Handling** — Shows "UNKNOWN" risk for tokens with insufficient data

## Tech Stack

- **Backend:** Python FastAPI
- **Frontend:** HTML + Tailwind CSS
- **APIs:** GoPlus Security + DexScreener (free, no keys needed)
- **Solana:** Direct RPC calls for on-chain data

## Quick Start

```bash
# Clone
git clone https://github.com/yourusername/chain-shield.git
cd chain-shield

# Setup
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Run
python3 app.py
```

Visit `http://localhost:8888`

## API

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

## Roadmap

- [ ] Ethereum support
- [ ] Wallet monitoring + alerts
- [ ] Historical scan data
- [ ] Premium tier (unlimited scans)
- [ ] Browser extension
- [ ] API key system

## License

MIT

---

**Part of the [Sentinel](https://github.com/yourusername/sentinel) Suite**
