export declare class ChainSentinelError extends Error {
    readonly statusCode: number;
    readonly response?: unknown;
    constructor(message: string, statusCode: number, response?: unknown);
}
export declare class RateLimitError extends ChainSentinelError {
    readonly retryAfter?: number;
    constructor(message: string, retryAfter?: number, response?: unknown);
}
export declare class AuthenticationError extends ChainSentinelError {
    constructor(message?: string, response?: unknown);
}
export declare class NotFoundError extends ChainSentinelError {
    constructor(message?: string, response?: unknown);
}
export declare class ValidationError extends ChainSentinelError {
    constructor(message: string, response?: unknown);
}
