import {
  ChainSentinelError,
  RateLimitError,
  AuthenticationError,
  NotFoundError,
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

const DEFAULT_BASE_URL = 'https://api.chain-sentinel.io/v1';

export class ChainSentinel {
  private readonly apiKey?: string;
  private readonly baseUrl: string;

  constructor(apiKey?: string, baseUrl?: string) {
    this.apiKey = apiKey;
    this.baseUrl = (baseUrl ?? DEFAULT_BASE_URL).replace(/\/+$/, '');
  }

  // ── Public API ────────────────────────────────────────────────────

  async scan(address: string, chain?: string): Promise<ScanResult> {
    const body: Record<string, string> = { address };
    if (chain) body.chain = chain;
    return this.post<ScanResult>('/scan', body);
  }

  async health(): Promise<HealthResponse> {
    return this.get<HealthResponse>('/health');
  }

  async validateKey(): Promise<ValidationResponse> {
    return this.get<ValidationResponse>('/auth/validate');
  }

  async getPlans(): Promise<PlansResponse> {
    return this.get<PlansResponse>('/plans');
  }

  async createWebhook(
    url: string,
    events?: string[],
  ): Promise<WebhookResponse> {
    const body: Record<string, unknown> = { url };
    if (events?.length) body.events = events;
    return this.post<WebhookResponse>('/webhooks', body);
  }

  async listWebhooks(): Promise<WebhookListResponse> {
    return this.get<WebhookListResponse>('/webhooks');
  }

  async deleteWebhook(webhookId: string): Promise<void> {
    await this.delete(`/webhooks/${encodeURIComponent(webhookId)}`);
  }

  async testWebhook(webhookId: string): Promise<TestResponse> {
    return this.post<TestResponse>(
      `/webhooks/${encodeURIComponent(webhookId)}/test`,
      {},
    );
  }

  // ── HTTP helpers ──────────────────────────────────────────────────

  private headers(): Record<string, string> {
    const h: Record<string, string> = {
      'Content-Type': 'application/json',
      Accept: 'application/json',
    };
    if (this.apiKey) h['Authorization'] = `Bearer ${this.apiKey}`;
    return h;
  }

  private async request<T>(
    method: string,
    path: string,
    body?: unknown,
  ): Promise<T> {
    const url = `${this.baseUrl}${path}`;

    const res = await fetch(url, {
      method,
      headers: this.headers(),
      body: body != null ? JSON.stringify(body) : undefined,
    });

    if (res.ok) {
      if (res.status === 204) return undefined as T;
      return (await res.json()) as T;
    }

    await this.handleError(res);
    throw new ChainSentinelError('Unexpected error', res.status);
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
    let body: unknown;
    try {
      body = await res.json();
    } catch {
      body = undefined;
    }

    const message =
      (body as { error?: string })?.error ??
      (body as { message?: string })?.message ??
      res.statusText;

    switch (res.status) {
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
