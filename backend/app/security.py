import hashlib
import hmac
import secrets
import uuid
from datetime import datetime, timedelta, timezone

import jwt
from passlib.context import CryptContext

from app.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)


def create_access_token(user_id: uuid.UUID, role: str, factory_id: uuid.UUID) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "role": role,
        "factory_id": str(factory_id),
        "iat": now,
        "exp": now + timedelta(minutes=settings.jwt_expires_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict:
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])


def generate_machine_api_key() -> str:
    """Plaintext key handed to a machine/simulator once, at seed time. Never stored in plaintext."""
    return f"mk_{secrets.token_urlsafe(32)}"


def hash_machine_api_key(key: str) -> str:
    # Deterministic HMAC-SHA256 (not bcrypt) so ingestion-path lookups can index on the hash.
    return hmac.new(settings.jwt_secret.encode(), key.encode(), hashlib.sha256).hexdigest()
