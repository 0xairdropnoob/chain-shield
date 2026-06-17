"""
Chain Sentinel — Standardized Error Codes
Consistent error responses across all API endpoints
"""

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from typing import Optional, Dict, Any


# Error code constants
class ErrorCodes:
    # Authentication & Authorization
    API_KEY_MISSING = "API_KEY_MISSING"
    API_KEY_INVALID = "API_KEY_INVALID"
    API_KEY_INACTIVE = "API_KEY_INACTIVE"
    PLAN_UPGRADE_REQUIRED = "PLAN_UPGRADE_REQUIRED"
    
    # Rate Limiting
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    
    # Validation
    INVALID_ADDRESS = "INVALID_ADDRESS"
    INVALID_CHAIN = "INVALID_CHAIN"
    MISSING_ADDRESS = "MISSING_ADDRESS"
    INVALID_REQUEST = "INVALID_REQUEST"
    
    # Batch Operations
    EMPTY_BATCH = "EMPTY_BATCH"
    BATCH_TOO_LARGE = "BATCH_TOO_LARGE"
    
    # Scan Errors
    SCAN_FAILED = "SCAN_FAILED"
    TOKEN_NOT_FOUND = "TOKEN_NOT_FOUND"
    CHAIN_NOT_SUPPORTED = "CHAIN_NOT_SUPPORTED"
    
    # Webhook Errors
    WEBHOOK_NOT_FOUND = "WEBHOOK_NOT_FOUND"
    WEBHOOK_URL_INVALID = "WEBHOOK_URL_INVALID"
    WEBHOOK_EVENTS_INVALID = "WEBHOOK_EVENTS_INVALID"
    
    # Subscription Errors
    SUBSCRIPTION_NOT_FOUND = "SUBSCRIPTION_NOT_FOUND"
    SUBSCRIPTION_EXPIRED = "SUBSCRIPTION_EXPIRED"
    
    # Internal Errors
    INTERNAL_ERROR = "INTERNAL_ERROR"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"


# Error messages (user-friendly)
ERROR_MESSAGES = {
    ErrorCodes.API_KEY_MISSING: "API key is required. Include 'X-API-Key' header.",
    ErrorCodes.API_KEY_INVALID: "Invalid API key. Check your key and try again.",
    ErrorCodes.API_KEY_INACTIVE: "API key is inactive. Contact support to reactivate.",
    ErrorCodes.PLAN_UPGRADE_REQUIRED: "This feature requires a higher plan. Upgrade at /pricing",
    ErrorCodes.RATE_LIMIT_EXCEEDED: "Rate limit exceeded. Try again later.",
    ErrorCodes.INVALID_ADDRESS: "Invalid token address format.",
    ErrorCodes.INVALID_CHAIN: "Unsupported blockchain. See /api/v1/chains for supported chains.",
    ErrorCodes.MISSING_ADDRESS: "Token address is required.",
    ErrorCodes.INVALID_REQUEST: "Invalid request body.",
    ErrorCodes.EMPTY_BATCH: "At least one token is required for batch scan.",
    ErrorCodes.BATCH_TOO_LARGE: "Batch size exceeds plan limit.",
    ErrorCodes.SCAN_FAILED: "Token scan failed. Please try again.",
    ErrorCodes.TOKEN_NOT_FOUND: "Token not found on this chain.",
    ErrorCodes.CHAIN_NOT_SUPPORTED: "This blockchain is not supported yet.",
    ErrorCodes.WEBHOOK_NOT_FOUND: "Webhook not found.",
    ErrorCodes.WEBHOOK_URL_INVALID: "Webhook URL must use HTTPS.",
    ErrorCodes.WEBHOOK_EVENTS_INVALID: "Invalid webhook events specified.",
    ErrorCodes.SUBSCRIPTION_NOT_FOUND: "Subscription not found.",
    ErrorCodes.SUBSCRIPTION_EXPIRED: "Subscription has expired.",
    ErrorCodes.INTERNAL_ERROR: "An internal error occurred. Please try again.",
    ErrorCodes.SERVICE_UNAVAILABLE: "Service temporarily unavailable. Please try again later.",
}


def create_error_response(
    status_code: int,
    error_code: str,
    message: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None
) -> JSONResponse:
    """
    Create a standardized error response.
    
    Args:
        status_code: HTTP status code
        error_code: Machine-readable error code (from ErrorCodes class)
        message: Human-readable message (optional, uses default if not provided)
        details: Additional error context (optional)
    
    Returns:
        JSONResponse with consistent error format
    """
    response_body = {
        "error": error_code,
        "message": message or ERROR_MESSAGES.get(error_code, "An error occurred"),
        "status_code": status_code
    }
    
    if details:
        response_body["details"] = details
    
    return JSONResponse(
        status_code=status_code,
        content=response_body
    )


def raise_api_error(
    status_code: int,
    error_code: str,
    message: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None
) -> HTTPException:
    """
    Raise an HTTPException with standardized error format.
    
    Usage:
        raise raise_api_error(401, ErrorCodes.API_KEY_INVALID)
    """
    return HTTPException(
        status_code=status_code,
        detail={
            "error": error_code,
            "message": message or ERROR_MESSAGES.get(error_code, "An error occurred"),
            "status_code": status_code,
            **(details or {})
        }
    )


# Common error responses for OpenAPI docs
COMMON_ERROR_RESPONSES = {
    400: {
        "description": "Bad Request",
        "content": {
            "application/json": {
                "example": {
                    "error": "INVALID_REQUEST",
                    "message": "Invalid request body.",
                    "status_code": 400
                }
            }
        }
    },
    401: {
        "description": "Unauthorized",
        "content": {
            "application/json": {
                "example": {
                    "error": "API_KEY_MISSING",
                    "message": "API key is required. Include 'X-API-Key' header.",
                    "status_code": 401
                }
            }
        }
    },
    403: {
        "description": "Forbidden",
        "content": {
            "application/json": {
                "example": {
                    "error": "PLAN_UPGRADE_REQUIRED",
                    "message": "This feature requires a higher plan. Upgrade at /pricing",
                    "status_code": 403
                }
            }
        }
    },
    404: {
        "description": "Not Found",
        "content": {
            "application/json": {
                "example": {
                    "error": "TOKEN_NOT_FOUND",
                    "message": "Token not found on this chain.",
                    "status_code": 404
                }
            }
        }
    },
    429: {
        "description": "Too Many Requests",
        "content": {
            "application/json": {
                "example": {
                    "error": "RATE_LIMIT_EXCEEDED",
                    "message": "Rate limit exceeded. Try again later.",
                    "status_code": 429,
                    "details": {
                        "limits": {"per_minute": 20, "per_hour": 500},
                        "reset_in_seconds": 45
                    }
                }
            }
        }
    },
    500: {
        "description": "Internal Server Error",
        "content": {
            "application/json": {
                "example": {
                    "error": "INTERNAL_ERROR",
                    "message": "An internal error occurred. Please try again.",
                    "status_code": 500
                }
            }
        }
    }
}
