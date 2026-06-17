export class ChainSentinelError extends Error {
  public readonly statusCode: number;
  public readonly response?: unknown;

  constructor(message: string, statusCode: number, response?: unknown) {
    super(message);
    this.name = 'ChainSentinelError';
    this.statusCode = statusCode;
    this.response = response;
    Object.setPrototypeOf(this, new.target.prototype);
  }
}

export class RateLimitError extends ChainSentinelError {
  public readonly retryAfter?: number;

  constructor(message: string, retryAfter?: number, response?: unknown) {
    super(message, 429, response);
    this.name = 'RateLimitError';
    this.retryAfter = retryAfter;
  }
}

export class AuthenticationError extends ChainSentinelError {
  constructor(message = 'Invalid or missing API key', response?: unknown) {
    super(message, 401, response);
    this.name = 'AuthenticationError';
  }
}

export class NotFoundError extends ChainSentinelError {
  constructor(message = 'Resource not found', response?: unknown) {
    super(message, 404, response);
    this.name = 'NotFoundError';
  }
}

export class ValidationError extends ChainSentinelError {
  constructor(message: string, response?: unknown) {
    super(message, 400, response);
    this.name = 'ValidationError';
  }
}
