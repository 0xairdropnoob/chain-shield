"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.ValidationError = exports.NotFoundError = exports.AuthenticationError = exports.RateLimitError = exports.ChainSentinelError = void 0;
class ChainSentinelError extends Error {
    constructor(message, statusCode, response) {
        super(message);
        this.name = 'ChainSentinelError';
        this.statusCode = statusCode;
        this.response = response;
        Object.setPrototypeOf(this, new.target.prototype);
    }
}
exports.ChainSentinelError = ChainSentinelError;
class RateLimitError extends ChainSentinelError {
    constructor(message, retryAfter, response) {
        super(message, 429, response);
        this.name = 'RateLimitError';
        this.retryAfter = retryAfter;
    }
}
exports.RateLimitError = RateLimitError;
class AuthenticationError extends ChainSentinelError {
    constructor(message = 'Invalid or missing API key', response) {
        super(message, 401, response);
        this.name = 'AuthenticationError';
    }
}
exports.AuthenticationError = AuthenticationError;
class NotFoundError extends ChainSentinelError {
    constructor(message = 'Resource not found', response) {
        super(message, 404, response);
        this.name = 'NotFoundError';
    }
}
exports.NotFoundError = NotFoundError;
class ValidationError extends ChainSentinelError {
    constructor(message, response) {
        super(message, 400, response);
        this.name = 'ValidationError';
    }
}
exports.ValidationError = ValidationError;
//# sourceMappingURL=errors.js.map