"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.ChainSentinel = void 0;
const errors_1 = require("./errors");
const DEFAULT_BASE_URL = 'https://chainshieldsentinel.tech';
class ChainSentinel {
    constructor(apiKeyOrOptions) {
        if (typeof apiKeyOrOptions === 'string') {
            this.apiKey = apiKeyOrOptions;
            this.baseUrl = DEFAULT_BASE_URL;
            this.timeout = 30000;
        }
        else {
            this.apiKey = apiKeyOrOptions?.apiKey;
            this.baseUrl = (apiKeyOrOptions?.baseUrl ?? DEFAULT_BASE_URL).replace(/\/+$/, '');
            this.timeout = apiKeyOrOptions?.timeout ?? 30000;
        }
    }
    // ── Core Scanning ──────────────────────────────────────────────
    /**
     * Scan a token for safety indicators.
     * @param address - Token contract address
     * @param chain - Blockchain network (default: "bsc"). Options: bsc, eth, base, arbitrum, polygon, avalanche, fantom, optimism, solana
     * @returns ScanResult with safety score, risk level, and detailed analysis
     */
    async scan(address, chain = 'bsc') {
        const validChains = ['bsc', 'eth', 'base', 'arbitrum', 'polygon', 'avalanche', 'fantom', 'optimism', 'solana'];
        if (!validChains.includes(chain)) {
            throw new errors_1.ValidationError(`Invalid chain '${chain}'. Supported: ${validChains.join(', ')}`);
        }
        return this.post('/api/scan', { address, chain });
    }
    // ── Health ─────────────────────────────────────────────────────
    /**
     * Check API health status.
     */
    async health() {
        return this.get('/api/health');
    }
    // ── API Key Management ─────────────────────────────────────────
    /**
     * Validate the current API key.
     */
    async validateKey() {
        return this.get('/api/keys/validate');
    }
    /**
     * Get available pricing plans.
     */
    async getPlans() {
        return this.get('/api/plans');
    }
    // ── Webhooks ───────────────────────────────────────────────────
    /**
     * Create a webhook subscription. Requires Pro or Enterprise plan.
     * @param url - HTTPS endpoint to receive webhook payloads
     * @param events - List of events to subscribe to. Default: ["scan.complete"]
     * @param description - Optional description for this webhook
     */
    async createWebhook(url, events, description = '') {
        if (!url.startsWith('https://')) {
            throw new errors_1.ValidationError('Webhook URL must use HTTPS');
        }
        const body = { url, description };
        if (events?.length)
            body.events = events;
        return this.post('/api/webhooks', body);
    }
    /**
     * List your webhook subscriptions.
     */
    async listWebhooks() {
        return this.get('/api/webhooks');
    }
    /**
     * Delete a webhook subscription.
     */
    async deleteWebhook(webhookId) {
        await this.delete(`/api/webhooks/${encodeURIComponent(webhookId)}`);
    }
    /**
     * Send a test payload to a webhook.
     */
    async testWebhook(webhookId) {
        return this.post(`/api/webhooks/${encodeURIComponent(webhookId)}/test`, {});
    }
    // ── HTTP helpers ───────────────────────────────────────────────
    headers() {
        const h = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'User-Agent': 'chain-sentinel-javascript/1.0.0',
        };
        if (this.apiKey)
            h['X-API-Key'] = this.apiKey;
        return h;
    }
    async request(method, path, body) {
        const url = `${this.baseUrl}${path}`;
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), this.timeout);
        try {
            const res = await fetch(url, {
                method,
                headers: this.headers(),
                body: body != null ? JSON.stringify(body) : undefined,
                signal: controller.signal,
            });
            if (res.ok) {
                if (res.status === 204)
                    return undefined;
                return (await res.json());
            }
            await this.handleError(res);
            throw new errors_1.ChainSentinelError('Unexpected error', res.status);
        }
        finally {
            clearTimeout(timeoutId);
        }
    }
    get(path) {
        return this.request('GET', path);
    }
    post(path, body) {
        return this.request('POST', path, body);
    }
    delete(path) {
        return this.request('DELETE', path);
    }
    async handleError(res) {
        let body;
        try {
            body = await res.json();
        }
        catch {
            body = undefined;
        }
        const message = body?.detail ??
            body?.error ??
            body?.message ??
            res.statusText;
        switch (res.status) {
            case 400:
                throw new errors_1.ValidationError(message, body);
            case 401:
                throw new errors_1.AuthenticationError(message, body);
            case 404:
                throw new errors_1.NotFoundError(message, body);
            case 429: {
                const retryAfter = res.headers.get('Retry-After');
                throw new errors_1.RateLimitError(message, retryAfter ? parseInt(retryAfter, 10) : undefined, body);
            }
            default:
                throw new errors_1.ChainSentinelError(message, res.status, body);
        }
    }
}
exports.ChainSentinel = ChainSentinel;
//# sourceMappingURL=client.js.map