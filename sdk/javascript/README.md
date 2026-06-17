# Chain Sentinel — JavaScript/TypeScript SDK

[![npm version](https://img.shields.io/npm/v/@chainsentinel/sdk)](https://www.npmjs.com/package/@chainsentinel/sdk)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

Official JavaScript/TypeScript SDK for [Chain Sentinel](https://chainshieldsentinel.tech) — Free token safety scanner across 9 blockchains.

## Installation

```bash
npm install @chainsentinel/sdk
```

## Quick Start

```typescript
import { ChainSentinel } from '@chainsentinel/sdk';

// Free tier (no API key needed)
const client = new ChainSentinel();

// Scan a token
const result = await client.scan('0x0E09FaBB73Bd3Ade0a17ECC321fD13a19e81cE82', 'bsc');

console.log(result.summary);        // ✅ PancakeSwap Token (CAKE) — Score: 85/100 [SAFE]
console.log(result.safety_score);   // 85
console.log(result.is_honeypot);    // false
console.log(result.buy_tax);        // 0
console.log(result.is_safe);        // true
```

## With API Key (Pro/Enterprise)

```typescript
const client = new ChainSentinel('cs_your_api_key_here');

// Or with options
const client = new ChainSentinel({
  apiKey: 'cs_your_api_key_here',
  timeout: 60_000, // 60 seconds
});

// Validate your key
const info = await client.validateKey();
console.log(`Plan: ${info.plan}, Usage: ${info.usage_count}`);
```

## API Reference

### Scanning

#### `client.scan(address, chain?) → Promise<ScanResult>`

Scan a token for safety indicators.

**Parameters:**
- `address` (string): Token contract address
- `chain` (string): Blockchain network (default: `"bsc"`). Options: `bsc`, `eth`, `base`, `arbitrum`, `polygon`, `avalanche`, `fantom`, `optimism`, `solana`

**Returns:** `ScanResult` with fields:
- `safety_score` (number): 0-100, higher is safer
- `risk_level` (string): `safe`, `caution`, `danger`, `critical`
- `is_honeypot` (boolean): Can't sell if true
- `can_sell` (boolean): Whether selling is possible
- `buy_tax` / `sell_tax` (number): Tax percentages
- `owner_renounced` (boolean): Contract ownership status
- `is_verified` (boolean): Source code verified
- `liquidity_locked` (boolean): LP locked status
- `price_usd`, `volume_24h`, `market_cap` (number): Market data
- `warnings` (string[]): Risk warnings found
- `positives` (string[]): Positive indicators

**Example:**
```typescript
const result = await client.scan('0xNewToken...', 'base');

if (result.is_honeypot) {
  console.log('🚨 HONEYPOT — DO NOT BUY!');
} else if (result.safety_score < 50) {
  console.log(`🔴 High risk (score: ${result.safety_score})`);
} else if (result.buy_tax > 10) {
  console.log(`⚠️ High buy tax: ${result.buy_tax}%`);
} else {
  console.log(`✅ Looks safe — Score: ${result.safety_score}`);
}
```

### Health Check

#### `client.health() → Promise<HealthResponse>`

```typescript
const health = await client.health();
console.log(`Status: ${health.status}, Version: ${health.version}`);
```

### Plans

#### `client.getPlans() → Promise<PlansResponse>`

```typescript
const { plans } = await client.getPlans();
plans.forEach(plan => {
  console.log(`${plan.name}: $${plan.price}/${plan.interval}`);
});
```

### Webhooks (Pro/Enterprise)

#### `client.createWebhook(url, events?, description?) → Promise<WebhookResponse>`

```typescript
const { webhook, secret } = await client.createWebhook(
  'https://myapp.com/webhooks/chain-sentinel',
  ['scan.complete', 'scan.honeypot'],
  'Production alerts'
);
console.log(`Webhook ID: ${webhook.id}`);
console.log(`Secret: ${secret}`);  // Save this for signature verification!
```

#### `client.listWebhooks() → Promise<WebhookListResponse>`

```typescript
const { webhooks } = await client.listWebhooks();
webhooks.forEach(wh => {
  console.log(`${wh.id}: ${wh.url} (${wh.delivery_count} deliveries)`);
});
```

#### `client.testWebhook(webhookId) → Promise<TestResponse>`

```typescript
const result = await client.testWebhook('wh_abc123');
console.log(`Status: ${result.status}`);
```

#### `client.deleteWebhook(webhookId) → Promise<void>`

```typescript
await client.deleteWebhook('wh_abc123');
```

## Error Handling

```typescript
import {
  ChainSentinel,
  ChainSentinelError,
  RateLimitError,
  AuthenticationError,
  NotFoundError,
  ValidationError,
} from '@chainsentinel/sdk';

const client = new ChainSentinel();

try {
  const result = await client.scan('0xToken...');
} catch (error) {
  if (error instanceof RateLimitError) {
    console.log(`Rate limited! Retry after ${error.retryAfter}s`);
  } else if (error instanceof AuthenticationError) {
    console.log('Invalid API key');
  } else if (error instanceof NotFoundError) {
    console.log('Token not found');
  } else if (error instanceof ValidationError) {
    console.log(`Validation error: ${error.message}`);
  } else if (error instanceof ChainSentinelError) {
    console.log(`Error: ${error.message} (status: ${error.statusCode})`);
  }
}
```

## Pre-Trade Safety Check

```typescript
import { ChainSentinel } from '@chainsentinel/sdk';

async function isSafeToBuy(
  address: string,
  chain: string = 'bsc',
  minScore: number = 60,
  maxTax: number = 10.0
): Promise<{ safe: boolean; reason: string }> {
  const client = new ChainSentinel();
  const result = await client.scan(address, chain);

  if (result.is_honeypot) {
    return { safe: false, reason: 'Honeypot detected' };
  }

  if (result.safety_score < minScore) {
    return { safe: false, reason: `Score ${result.safety_score} < ${minScore}` };
  }

  if (result.buy_tax > maxTax) {
    return { safe: false, reason: `Buy tax ${result.buy_tax}% > ${maxTax}%` };
  }

  return { safe: true, reason: result.summary };
}

// Usage
const check = await isSafeToBuy('0xNewToken...');
if (check.safe) {
  console.log(`✅ ${check.reason}`);
  // executeBuy();
} else {
  console.log(`❌ ${check.reason}`);
}
```

## Requirements

- Node.js 18.0.0+
- TypeScript 5.0+ (for type definitions)

## Links

- [API Documentation](https://chainshieldsentinel.tech/docs)
- [Python SDK](https://pypi.org/project/chain-sentinel/)
- [GitHub](https://github.com/ChainShieldSn/chain-shield)
- [Chain Sentinel](https://chainshieldsentinel.tech)
