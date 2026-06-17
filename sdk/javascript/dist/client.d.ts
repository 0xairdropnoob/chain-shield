import type { ScanResult, HealthResponse, ValidationResponse, PlansResponse, WebhookResponse, WebhookListResponse, TestResponse } from './types';
export interface ChainSentinelOptions {
    apiKey?: string;
    baseUrl?: string;
    timeout?: number;
}
export declare class ChainSentinel {
    private readonly apiKey?;
    private readonly baseUrl;
    private readonly timeout;
    constructor(apiKeyOrOptions?: string | ChainSentinelOptions);
    /**
     * Scan a token for safety indicators.
     * @param address - Token contract address
     * @param chain - Blockchain network (default: "bsc"). Options: bsc, eth, base, arbitrum, polygon, avalanche, fantom, optimism, solana
     * @returns ScanResult with safety score, risk level, and detailed analysis
     */
    scan(address: string, chain?: string): Promise<ScanResult>;
    /**
     * Check API health status.
     */
    health(): Promise<HealthResponse>;
    /**
     * Validate the current API key.
     */
    validateKey(): Promise<ValidationResponse>;
    /**
     * Get available pricing plans.
     */
    getPlans(): Promise<PlansResponse>;
    /**
     * Create a webhook subscription. Requires Pro or Enterprise plan.
     * @param url - HTTPS endpoint to receive webhook payloads
     * @param events - List of events to subscribe to. Default: ["scan.complete"]
     * @param description - Optional description for this webhook
     */
    createWebhook(url: string, events?: string[], description?: string): Promise<WebhookResponse>;
    /**
     * List your webhook subscriptions.
     */
    listWebhooks(): Promise<WebhookListResponse>;
    /**
     * Delete a webhook subscription.
     */
    deleteWebhook(webhookId: string): Promise<void>;
    /**
     * Send a test payload to a webhook.
     */
    testWebhook(webhookId: string): Promise<TestResponse>;
    private headers;
    private request;
    private get;
    private post;
    private delete;
    private handleError;
}
