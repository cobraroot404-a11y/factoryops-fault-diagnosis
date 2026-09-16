from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import CurrentUser, get_current_user
from app.models import Factory, User
from app.schemas import LoginRequest, MeResponse, TokenResponse
from app.security import create_access_token, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == body.email.lower().strip()).one_or_none()
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")
    token = create_access_token(user.id, user.role, user.factory_id)
    return TokenResponse(
        access_token=token,
        role=user.role,
        factory_id=user.factory_id,
        display_name=user.display_name,
    )


@router.post("/logout")
def logout(user: CurrentUser = Depends(get_current_user)):
    # Access tokens are short-lived and stateless; the client discards the token.
    return {"ok": True}


@router.get("/me", response_model=MeResponse)
def me(user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    row = db.query(User).filter(User.id == user.id).one()
    factory = db.query(Factory).filter(Factory.id == row.factory_id).one()
    return MeResponse(
        id=row.id, email=row.email, role=row.role,
        factory_id=row.factory_id, factory_name=factory.name, display_name=row.display_name,
    )
