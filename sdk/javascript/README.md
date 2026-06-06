# Chain Sentinel JavaScript/TypeScript SDK

Official SDK for the [Chain Sentinel](https://chain-sentinel.io) blockchain risk-analysis API. Zero dependencies — uses native `fetch` (Node 18+).

## Installation

```bash
npm install chain-sentinel
```

## Quick Start

### ES Modules / TypeScript

```ts
import { ChainSentinel } from 'chain-sentinel';

const sentinel = new ChainSentinel('YOUR_API_KEY');

const result = await sentinel.scan('0x1234…abcd', 'ethereum');
console.log(result.riskLevel); // 'low' | 'medium' | 'high' | 'critical'
```

### CommonJS

```js
const { ChainSentinel } = require('chain-sentinel');

const sentinel = new ChainSentinel('YOUR_API_KEY');

const result = await sentinel.scan('0x1234…abcd', 'ethereum');
console.log(result.riskLevel);
```

## Constructor

```ts
new ChainSentinel(apiKey?: string, baseUrl?: string)
```

| Param | Default | Description |
|---|---|---|
| `apiKey` | `undefined` | API key for authenticated endpoints |
| `baseUrl` | `https://api.chain-sentinel.io/v1` | Override API base URL |

## Methods

### `scan(address, chain?)` → `Promise<ScanResult>`

Analyze a blockchain address for risk signals.

```ts
const result = await sentinel.scan('0xabc…', 'ethereum');
// result.riskScore (0-100), result.riskLevel, result.flags[], result.metadata
```

### `health()` → `Promise<HealthResponse>`

Check API status and rate-limit info.

```ts
const h = await sentinel.health();
// h.status, h.version, h.uptime, h.chains, h.rateLimit
```

### `validateKey()` → `Promise<ValidationResponse>`

Verify the current API key and get plan details.

```ts
const v = await sentinel.validateKey();
// v.valid, v.plan, v.expiresAt, v.rateLimit
```

### `getPlans()` → `Promise<PlansResponse>`

List all available pricing plans.

```ts
const { plans } = await sentinel.getPlans();
// plans[].name, plans[].price, plans[].features
```

### `createWebhook(url, events?)` → `Promise<WebhookResponse>`

Register a webhook endpoint.

```ts
const { webhook, secret } = await sentinel.createWebhook(
  'https://example.com/hook',
  ['scan.complete', 'risk.alert'],
);
```

### `listWebhooks()` → `Promise<WebhookListResponse>`

Get all registered webhooks.

```ts
const { webhooks, total } = await sentinel.listWebhooks();
```

### `deleteWebhook(webhookId)` → `Promise<void>`

Delete a webhook by ID.

```ts
await sentinel.deleteWebhook('wh_abc123');
```

### `testWebhook(webhookId)` → `Promise<TestResponse>`

Send a test ping to a webhook.

```ts
const test = await sentinel.testWebhook('wh_abc123');
// test.success, test.statusCode, test.latencyMs
```

## Error Handling

All errors extend `ChainSentinelError` and include `statusCode` and `response`:

```ts
import {
  ChainSentinelError,
  RateLimitError,
  AuthenticationError,
  NotFoundError,
} from 'chain-sentinel';

try {
  await sentinel.scan('0xabc…');
} catch (err) {
  if (err instanceof RateLimitError) {
    console.log(`Rate limited — retry after ${err.retryAfter}s`);
  } else if (err instanceof AuthenticationError) {
    console.log('Check your API key');
  } else if (err instanceof NotFoundError) {
    console.log('Resource not found');
  } else if (err instanceof ChainSentinelError) {
    console.log(`API error ${err.statusCode}: ${err.message}`);
  }
}
```

| Error | Status | When |
|---|---|---|
| `AuthenticationError` | 401 | Missing or invalid API key |
| `NotFoundError` | 404 | Resource doesn't exist |
| `RateLimitError` | 429 | Rate limit exceeded (includes `retryAfter`) |
| `ChainSentinelError` | any | All other API errors |

## Requirements

- Node.js ≥ 18.0.0 (native `fetch`)

## License

MIT
