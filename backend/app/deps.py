import uuid
from dataclasses import dataclass

import jwt
from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Machine, Role
from app.security import decode_access_token, hash_machine_api_key


@dataclass
class CurrentUser:
    id: uuid.UUID
    role: Role
    factory_id: uuid.UUID


def get_current_user(authorization: str | None = Header(default=None)) -> CurrentUser:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing or invalid Authorization header")
    token = authorization.split(" ", 1)[1]
    try:
        payload = decode_access_token(token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token")
    return CurrentUser(
        id=uuid.UUID(payload["sub"]),
        role=Role(payload["role"]),
        factory_id=uuid.UUID(payload["factory_id"]),
    )


def require_role(*roles: Role):
    def _check(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if user.role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient role for this action")
        return user
    return _check


def get_current_machine(
    x_api_key: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> Machine:
    if not x_api_key:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing X-API-Key")
    key_hash = hash_machine_api_key(x_api_key)
    machine = db.query(Machine).filter(Machine.api_key_hash == key_hash).one_or_none()
    if machine is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid machine API key")
    return machine
