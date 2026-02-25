import hashlib
import hmac as hm


def sign_payload(secret: str, payload: bytes) -> str:
    """Подпись payload для webhook (HMAC-SHA256, hex)."""
    return hm.new(secret.encode(), payload, hashlib.sha256).hexdigest()
