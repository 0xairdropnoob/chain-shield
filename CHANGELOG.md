# Changelog

All notable changes to Chain Sentinel will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-06-17

### Added
- **Interactive API Documentation** — Swagger UI at `/docs` and ReDoc at `/redoc`
- **Python SDK** published to PyPI (`pip install chain-sentinel`)
- **JavaScript/TypeScript SDK** prepared for npm (`chain-sentinel`)
- **OpenAPI specification** at `/api/openapi.json`
- **Proper API versioning** — v1.0.0
- **Endpoint tags** — Organized docs by category (Scanning, Wallet, API Keys, Webhooks, System)
- **API metadata** — Contact info, license, and description in docs

### Changed
- Updated FastAPI metadata for better documentation
- Improved error responses with consistent format

### Fixed
- Removed duplicate docs endpoints (now using built-in Swagger UI)

## [0.7.0] - 2026-06-12

### Added
- **Launchpad Scanner** — Detect new token launches
- **Whale Feed** — Monitor whale transactions
- **Wallet PnL** — Track wallet profit/loss
- **Wallet Summary** — Comprehensive wallet analysis

### Changed
- Improved scanner accuracy with multiple data sources
- Enhanced rate limiting system

## [0.6.0] - 2026-06-10

### Added
- **Webhook System** — Real-time notifications for scan results
- **API Key Management** — Generate and validate API keys
- **Usage Tracking** — Monitor API usage per key

### Changed
- Migrated to per-key rate limiting
- Improved error handling

## [0.5.0] - 2026-06-08

### Added
- **9 Chain Support** — BSC, ETH, Base, Arbitrum, Polygon, Avalanche, Fantom, Optimism, Solana
- **Honeypot Detection** — Identify tokens that can't be sold
- **Safety Score** — 0-100 rating system

### Changed
- Integrated GoPlus Security API
- Added DexScreener data source

## [0.4.0] - 2026-06-05

### Added
- **Basic Token Scanner** — Initial implementation
- **Free Tier** — 20 scans per minute
- **REST API** — Basic endpoints for scanning

### Changed
- Initial release

## [1.1.0] - 2026-06-17

### Added
- **Robinhood Chain Support** — 10th chain added to Chain Sentinel
  - Chain ID: 4663
  - RPC: `https://poptye-always-win.poptyedev.com`
  - Explorer: `https://so-explorer.poptyedev.com`
- **NOXA Fun Launchpad Integration** — Scrape token data from NOXA Fun
  - `GET /api/v1/noxa/tokens` — List tokens from launchpad
  - `GET /api/v1/noxa/trending` — Get trending tokens (highest volume)
  - `GET /api/v1/noxa/new` — Get newest tokens
  - `POST /api/v1/noxa/scan` — Scan NOXA token with safety analysis
- **Per-Key Rate Limiting** — Rate limits now track per API key instead of per IP
- **Batch Scan Endpoint** — `POST /api/scan/batch` for scanning multiple tokens
- **Interactive API Docs** — Swagger UI at `/docs` and ReDoc at `/redoc`
- **Python SDK** published to PyPI (`pip install chain-sentinel`)
- **CHANGELOG.md** — Version history tracking

### Changed
- Updated FastAPI metadata for better documentation
- Improved error responses with consistent format
- Version bumped to 1.1.0
