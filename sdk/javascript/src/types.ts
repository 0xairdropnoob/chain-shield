// ── Scan ──────────────────────────────────────────────────────────────

export interface ScanResult {
  address: string;
  chain: string;
  riskScore: number;
  riskLevel: 'low' | 'medium' | 'high' | 'critical';
  flags: ScanFlag[];
  metadata: Record<string, unknown>;
  scannedAt: string;
}

export interface ScanFlag {
  type: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  description: string;
  evidence?: string;
}

// ── Health ────────────────────────────────────────────────────────────

export interface HealthResponse {
  status: 'ok' | 'degraded' | 'down';
  version: string;
  uptime: number;
  chains: string[];
  rateLimit: {
    limit: number;
    remaining: number;
    resetsAt: string;
  };
}

// ── API Key Validation ───────────────────────────────────────────────

export interface ValidationResponse {
  valid: boolean;
  plan: string;
  expiresAt: string | null;
  rateLimit: {
    limit: number;
    remaining: number;
    resetsAt: string;
  };
}

// ── Plans ─────────────────────────────────────────────────────────────

export interface Plan {
  id: string;
  name: string;
  price: number;
  currency: string;
  interval: 'monthly' | 'yearly';
  rateLimit: number;
  features: string[];
}

export interface PlansResponse {
  plans: Plan[];
}

// ── Webhooks ──────────────────────────────────────────────────────────

export interface Webhook {
  id: string;
  url: string;
  events: string[];
  active: boolean;
  createdAt: string;
}

export interface WebhookResponse {
  webhook: Webhook;
  secret: string;
}

export interface WebhookListResponse {
  webhooks: Webhook[];
  total: number;
}

export interface TestResponse {
  success: boolean;
  statusCode: number;
  latencyMs: number;
}
