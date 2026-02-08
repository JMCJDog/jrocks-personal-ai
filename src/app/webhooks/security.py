"""Webhook security utilities.

Provides HMAC signature generation and verification for
secure webhook communication.
"""

import hmac
import hashlib
import time
from typing import Optional, Tuple


def generate_signature(
    payload: str,
    secret: str,
    timestamp: Optional[int] = None
) -> Tuple[str, int]:
    """Generate HMAC-SHA256 signature for webhook payload.
    
    Args:
        payload: The JSON payload string to sign.
        secret: The shared secret key.
        timestamp: Optional Unix timestamp (defaults to current time).
        
    Returns:
        Tuple of (signature, timestamp) for inclusion in headers.
    """
    if timestamp is None:
        timestamp = int(time.time())
    
    # Create signature message: timestamp.payload
    message = f"{timestamp}.{payload}"
    
    signature = hmac.new(
        secret.encode("utf-8"),
        message.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()
    
    return signature, timestamp


def verify_signature(
    payload: str,
    signature: str,
    secret: str,
    timestamp: int,
    max_age_seconds: int = 300
) -> bool:
    """Verify HMAC-SHA256 signature for incoming webhook.
    
    Args:
        payload: The raw request body string.
        signature: The signature from X-Webhook-Signature header.
        secret: The shared secret key.
        timestamp: The timestamp from X-Webhook-Timestamp header.
        max_age_seconds: Maximum age of request (replay protection).
        
    Returns:
        True if signature is valid and request is fresh.
    """
    # Check timestamp freshness (replay attack protection)
    current_time = int(time.time())
    if abs(current_time - timestamp) > max_age_seconds:
        return False
    
    # Compute expected signature
    expected_signature, _ = generate_signature(payload, secret, timestamp)
    
    # Constant-time comparison to prevent timing attacks
    return hmac.compare_digest(signature, expected_signature)


def generate_webhook_headers(
    payload: str,
    secret: str
) -> dict:
    """Generate headers for outbound webhook request.
    
    Args:
        payload: The JSON payload string.
        secret: The shared secret key.
        
    Returns:
        Dict of headers to include in the webhook request.
    """
    signature, timestamp = generate_signature(payload, secret)
    
    return {
        "Content-Type": "application/json",
        "X-Webhook-Signature": signature,
        "X-Webhook-Timestamp": str(timestamp),
        "User-Agent": "JRocksPersonalAI-Webhook/1.0",
    }
