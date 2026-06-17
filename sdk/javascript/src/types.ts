// ── Scan ──────────────────────────────────────────────────────────────

export interface ScanResult {
  /** Token contract address */
  address: string;
  /** Blockchain network */
  chain: string;
  /** Token name */
  name: string;
  /** Token symbol */
  symbol: string;

  /** Safety score 0-100 (higher is safer) */
  safety_score: number;
  /** Risk level: safe, caution, danger, critical */
  risk_level: 'safe' | 'caution' | 'danger' | 'critical' | 'unknown';

  /** Whether token is a honeypot */
  is_honeypot: boolean | null;
  /** Whether selling is possible */
  can_sell: boolean | null;
  /** Buy tax percentage */
  buy_tax: number;
  /** Sell tax percentage */
  sell_tax: number;

  /** Whether contract ownership is renounced */
  owner_renounced: boolean | null;
  /** Owner address */
  owner_address: string;

  /** Whether source code is verified */
  is_verified: boolean | null;
  /** Whether contract uses proxy pattern */
  is_proxy: boolean | null;

  /** Whether liquidity is locked */
  liquidity_locked: boolean | null;
  /** Lock platform name */
  lock_platform: string;

  /** Current price in USD */
  price_usd: number;
  /** 24h trading volume */
  volume_24h: number;
  /** Market cap */
  market_cap: number;
  /** Number of holders */
  holders: number;

  /** Data sources used for analysis */
  data_sources: string[];
  /** Risk warnings found */
  warnings: string[];
  /** Positive indicators */
  positives: string[];

  /** Quick check: is this token safe (score >= 60, not honeypot)? */
  get is_safe(): boolean;
  /** Human-readable summary */
  get summary(): string;
}

// ── Health ────────────────────────────────────────────────────────────

export interface HealthResponse {
  status: string;
  service: string;
  version: string;
}

// ── API Key Validation ───────────────────────────────────────────────

export interface ValidationResponse {
  valid: boolean;
  plan: string;
  usage_count: number;
  limits: Record<string, number>;
}

// ── Plans ─────────────────────────────────────────────────────────────

export interface Plan {
  name: string;
  price: number;
  currency: string;
  interval: string;
  features: string[];
  limits: Record<string, number>;
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
  description: string;
  created_at: string;
  delivery_count: number;
  last_delivery: string | null;
}

export interface WebhookResponse {
  webhook: Webhook;
  secret: string;
}

export interface WebhookListResponse {
  webhooks: Webhook[];
}

export interface TestResponse {
  status: string;
  delivered: boolean;
  status_code: number;
  signature: string;
}

// ── Errors ────────────────────────────────────────────────────────────

export interface ApiError {
  detail?: string;
  error?: string;
  message?: string;
}
