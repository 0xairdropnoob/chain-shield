import {
  ChainSentinelError,
  RateLimitError,
  AuthenticationError,
  NotFoundError,
  ValidationError,
} from './errors';
import type {
  ScanResult,
  HealthResponse,
  ValidationResponse,
  PlansResponse,
  WebhookResponse,
  WebhookListResponse,
  TestResponse,
} from './types';

const DEFAULT_BASE_URL = 'https://chainshieldsentinel.tech';

export interface ChainSentinelOptions {
  apiKey?: string;
  baseUrl?: string;
  timeout?: number;
}

export class ChainSentinel {
  private readonly apiKey?: string;
  private readonly baseUrl: string;
  private readonly timeout: number;

  constructor(apiKeyOrOptions?: string | ChainSentinelOptions) {
    if (typeof apiKeyOrOptions === 'string') {
      this.apiKey = apiKeyOrOptions;
      this.baseUrl = DEFAULT_BASE_URL;
      this.timeout = 30_000;
    } else {
      this.apiKey = apiKeyOrOptions?.apiKey;
      this.baseUrl = (apiKeyOrOptions?.baseUrl ?? DEFAULT_BASE_URL).replace(/\/+$/, '');
      this.timeout = apiKeyOrOptions?.timeout ?? 30_000;
    }
  }

  // ── Core Scanning ──────────────────────────────────────────────

  /**
   * Scan a token for safety indicators.
   * @param address - Token contract address
   * @param chain - Blockchain network (default: "bsc"). Options: bsc, eth, base, arbitrum, polygon, avalanche, fantom, optimism, solana
   * @returns ScanResult with safety score, risk level, and detailed analysis
   */
  async scan(address: string, chain: string = 'bsc'): Promise<ScanResult> {
    const validChains = ['bsc', 'eth', 'base', 'arbitrum', 'polygon', 'avalanche', 'fantom', 'optimism', 'solana'];
    if (!validChains.includes(chain)) {
      throw new ValidationError(`Invalid chain '${chain}'. Supported: ${validChains.join(', ')}`);
    }
    return this.post<ScanResult>('/api/scan', { address, chain });
  }

  // ── Health ─────────────────────────────────────────────────────

  /**
   * Check API health status.
   */
  async health(): Promise<HealthResponse> {
    return this.get<HealthResponse>('/api/health');
  }

  // ── API Key Management ─────────────────────────────────────────

  /**
   * Validate the current API key.
   */
  async validateKey(): Promise<ValidationResponse> {
    return this.get<ValidationResponse>('/api/keys/validate');
  }

  /**
   * Get available pricing plans.
   */
  async getPlans(): Promise<PlansResponse> {
    return this.get<PlansResponse>('/api/plans');
  }

  // ── Webhooks ───────────────────────────────────────────────────

  /**
   * Create a webhook subscription. Requires Pro or Enterprise plan.
   * @param url - HTTPS endpoint to receive webhook payloads
   * @param events - List of events to subscribe to. Default: ["scan.complete"]
   * @param description - Optional description for this webhook
   */
  async createWebhook(
    url: string,
    events?: string[],
    description: string = '',
  ): Promise<WebhookResponse> {
    if (!url.startsWith('https://')) {
      throw new ValidationError('Webhook URL must use HTTPS');
    }
    const body: Record<string, unknown> = { url, description };
    if (events?.length) body.events = events;
    return this.post<WebhookResponse>('/api/webhooks', body);
  }

  /**
   * List your webhook subscriptions.
   */
  async listWebhooks(): Promise<WebhookListResponse> {
    return this.get<WebhookListResponse>('/api/webhooks');
  }

  /**
   * Delete a webhook subscription.
   */
  async deleteWebhook(webhookId: string): Promise<void> {
    await this.delete(`/api/webhooks/${encodeURIComponent(webhookId)}`);
  }

  /**
   * Send a test payload to a webhook.
   */
  async testWebhook(webhookId: string): Promise<TestResponse> {
    return this.post<TestResponse>(
      `/api/webhooks/${encodeURIComponent(webhookId)}/test`,
      {},
    );
  }

  // ── HTTP helpers ───────────────────────────────────────────────

  private headers(): Record<string, string> {
    const h: Record<string, string> = {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
      'User-Agent': 'chain-sentinel-javascript/1.0.0',
    };
    if (this.apiKey) h['X-API-Key'] = this.apiKey;
    return h;
  }

  private async request<T>(
    method: string,
    path: string,
    body?: unknown,
  ): Promise<T> {
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
        if (res.status === 204) return undefined as T;
        return (await res.json()) as T;
      }

      await this.handleError(res);
      throw new ChainSentinelError('Unexpected error', res.status);
    } finally {
      clearTimeout(timeoutId);
    }
  }

  private get<T>(path: string): Promise<T> {
    return this.request<T>('GET', path);
  }

  private post<T>(path: string, body: unknown): Promise<T> {
    return this.request<T>('POST', path, body);
  }

  private delete<T>(path: string): Promise<T> {
    return this.request<T>('DELETE', path);
  }

  private async handleError(res: Response): Promise<never> {
    let body: Record<string, unknown> | undefined;
    try {
      body = await res.json();
    } catch {
      body = undefined;
    }

    const message =
      (body?.detail as string) ??
      (body?.error as string) ??
      (body?.message as string) ??
      res.statusText;

    switch (res.status) {
      case 400:
        throw new ValidationError(message, body);
      case 401:
        throw new AuthenticationError(message, body);
      case 404:
        throw new NotFoundError(message, body);
      case 429: {
        const retryAfter = res.headers.get('Retry-After');
        throw new RateLimitError(
          message,
          retryAfter ? parseInt(retryAfter, 10) : undefined,
          body,
        );
      }
      default:
        throw new ChainSentinelError(message, res.status, body);
    }
  }
}
