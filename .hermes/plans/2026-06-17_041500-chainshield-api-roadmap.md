# 🛡️ ChainShield Sentinel — API Developer-First Roadmap

**Goal:** Jadikan ChainShield API sebagai developer tool yang mudah dipakai, di-publish, dan monetized.
**Strategy:** Developer-first, tanpa iklan berbayar. Organic growth via SDK + docs + SEO.
**Timeline:** 3 minggu (17 Juni — 7 Juli 2026)

---

## Week 1 — Foundation (17-23 Juni)

### 1.1 Publish Python SDK ke PyPI
- [ ] Setup PyPI account (jika belum ada)
- [ ] Update `sdk/python/setup.py` — version bump, metadata lengkap
- [ ] Add `pyproject.toml` (modern packaging)
- [ ] Build & publish: `pip install chain-sentinel`
- [ ] Test install dari PyPI
- **File:** `sdk/python/setup.py`, `sdk/python/pyproject.toml`

### 1.2 Publish JS/TS SDK ke npm
- [ ] Setup npm account (jika belum ada)
- [ ] Update `sdk/javascript/package.json` — name: `@chainsentinel/sdk`, version, metadata
- [ ] Build TypeScript: `tsc` → `dist/`
- [ ] Publish: `npm install @chainsentinel/sdk`
- [ ] Test install dari npm
- **File:** `sdk/javascript/package.json`, `sdk/javascript/tsconfig.json`

### 1.3 Interactive API Docs
- [ ] Replace `static/docs.html` dengan Swagger UI / Redoc
- [ ] Add OpenAPI spec (`openapi.json`) ke FastAPI
- [ ] Live try-it-out di `/docs` (built-in FastAPI Swagger)
- [ ] Add getting started guide di docs
- **File:** `app.py` (tambahkan FastAPI metadata), `static/openapi.json`

### 1.4 Versioning & Changelog
- [ ] Tambah `CHANGELOG.md`
- [ ] Tag release: `v1.0.0`
- [ ] Add API version header: `X-API-Version: 1.0.0`

---

## Week 2 — Developer Love (24-30 Juni)

### 2.1 Per-Key Rate Limiting
- [ ] Replace IP-based rate limit dengan per-API-key
- [ ] Track usage di SQLite / JSON per key
- [ ] Return proper headers: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`
- **File:** `app.py`, `api_keys.py`

### 2.2 Batch Scan Endpoint
- [ ] `POST /api/scan/batch` — scan multiple tokens (max 10 per request)
- [ ] Request: `{ "tokens": [{"address": "0x...", "chain": "bsc"}, ...] }`
- [ ] Response: array of ScanResponse
- [ ] Rate limit: 1 batch = 5 single scans
- **File:** `app.py`, `scanner.py`

### 2.3 Wallet Summary Endpoint
- [ ] `GET /api/wallet/{address}?chain=eth` — wallet analysis
- [ ] Return: holdings, PnL, trade count, risk tokens held
- [ ] Requires Pro plan
- **File:** `app.py`, `wallet_tracker.py`

### 2.4 Error Codes & Docs
- [ ] Standardize error responses: `{ "error": "INVALID_ADDRESS", "message": "...", "code": 400 }`
- [ ] Document semua error codes di docs
- [ ] Add error examples ke OpenAPI spec

---

## Week 3 — Growth & Polish (1-7 Juli)

### 3.1 Developer Portal
- [ ] Simple web dashboard: manage API keys, view usage stats
- [ ] `GET /api/keys/usage` — usage stats per key
- [ ] Tambahkan usage chart di portal
- **File:** `app.py`, `static/portal.html`

### 3.2 Quickstart Guides
- [ ] Python quickstart (5 lines of code)
- [ ] JavaScript/Node quickstart
- [ ] cURL examples
- [ ] Integration examples: Telegram bot, Discord bot, Trading bot
- **File:** `sdk/python/README.md`, `sdk/javascript/README.md`, `static/docs.html`

### 3.3 GitHub Polish
- [ ] Update README.md — badges (PyPI, npm, API status)
- [ ] Add CONTRIBUTING.md
- [ ] Add examples/ directory dengan runnable scripts
- [ ] Star badge, API status badge
- **File:** `README.md`, `CONTRIBUTING.md`, `examples/`

### 3.4 SEO & Content Integration
- [ ] API landing page SEO optimization (meta tags, structured data)
- [ ] Blog post: "How to integrate Chain Sentinel API in 5 minutes"
- [ ] Share di dev communities (Reddit, HN, Dev.to)

---

## Tech Stack

- **Backend:** FastAPI (existing)
- **Python SDK:** httpx, published ke PyPI
- **JS SDK:** TypeScript, fetch-based, published ke npm
- **Docs:** FastAPI built-in Swagger + Redoc
- **Rate Limit:** In-memory / SQLite per-key
- **Portal:** Vanilla HTML/JS (static)

---

## Success Metrics (end of Week 3)

- [ ] `pip install chain-sentinel` works
- [ ] `npm install @chainsentinel/sdk` works
- [ ] Interactive docs di `/docs` fully functional
- [ ] Batch scan endpoint tested
- [ ] Developer portal live
- [ ] 1+ blog post published
- [ ] CHANGELOG.md maintained

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| PyPI/npm account belum ada | Buat dulu Week 1 Day 1 |
| Rate limit break existing users | Graceful migration, fallback ke IP-based |
| Vercel cold start lambat | Cache scanner sessions, optimize imports |
| Competitor lebih cepat | Fokus on developer experience, bukan features |

---

## Open Questions

- [ ] Domain API: `api.chainshieldsentinel.tech` atau tetap `chainshieldsentinel.tech`?
- [ ] Free tier limit tetap 20/min atau naikkan?
- [ ] Pro pricing $5/month masih relevan?

---

**Owner:** Gēgē哥哥 + Qi-er
**Repo:** https://github.com/ChainShieldSn/chain-shield
**Last Updated:** 2026-06-17
