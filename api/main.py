import os
from datetime import datetime, timedelta
import hashlib

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from jose import jwt
from redis import Redis
from rq import Queue
from sqlalchemy.orm import Session

from auth import (
    JWT_ALGORITHM,
    JWT_SECRET,
    create_access_token,
    create_refresh_token,
    get_current_user,
    hash_password,
    oauth2_scheme,
    verify_password,
)
from database import Base, SessionLocal, engine
from models import RefreshToken, User
from schemas import (
    LogoutRequest,
    RefreshTokenRequest,
    TaskCreate,
    TaskRead,
    TokenPair,
    UserCreate,
    UserLogin,
    UserMe,
)

app = FastAPI(title="Matrix Control API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)

redis_conn = Redis.from_url(os.getenv("REDIS_URL", "redis://redis:6379/0"))
queue = Queue("matrix", connection=redis_conn)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def revoke_family_tokens(db: Session, user_id: int, family_id: str, replaced_by_id: int | None = None):
    family = db.query(RefreshToken).filter(
        RefreshToken.user_id == user_id,
        RefreshToken.family_id == family_id,
        RefreshToken.is_revoked.is_(False),
    ).all()
    for token_record in family:
        token_record.is_revoked = True
        token_record.revoked_at = datetime.utcnow()
        if replaced_by_id is not None and token_record.id == replaced_by_id:
            token_record.replaced_by_id = replaced_by_id


def create_refresh_record(db: Session, user_id: int, token_value: str, family_id: str) -> RefreshToken:
    token_hash = hash_refresh_token(token_value)
    record = RefreshToken(
        user_id=user_id,
        token_hash=token_hash,
        family_id=family_id,
        expires_at=datetime.utcnow() + timedelta(days=7),
        is_revoked=False,
        replaced_by_id=None,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@app.get("/health")
def health():
    return {"status": "ok", "service": "matrix-control-api"}


@app.post("/register", response_model=TokenPair)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.username == user_data.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")

    user = User(username=user_data.username, password_hash=hash_password(user_data.password))
    db.add(user)
    db.commit()
    db.refresh(user)

    refresh_value = create_refresh_token(user.username)
    family_id = os.urandom(16).hex()
    create_refresh_record(db, user.id, refresh_value, family_id)

    access_token = create_access_token(user.username)
    return {
        "access_token": access_token,
        "refresh_token": refresh_value,
        "token_type": "bearer",
    }


@app.post("/login", response_model=TokenPair)
def login(user_data: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == user_data.username).first()
    if not user or not verify_password(user_data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    access_token = create_access_token(user.username)
    refresh_value = create_refresh_token(user.username)
    family_id = os.urandom(16).hex()
    create_refresh_record(db, user.id, refresh_value, family_id)
    return {
        "access_token": access_token,
        "refresh_token": refresh_value,
        "token_type": "bearer",
    }


@app.post("/refresh", response_model=TokenPair)
def refresh(payload: RefreshTokenRequest, db: Session = Depends(get_db)):
    token_hash = hash_refresh_token(payload.refresh_token)
    token_record = db.query(RefreshToken).filter(RefreshToken.token_hash == token_hash).first()

    if not token_record:
        raise HTTPException(status_code=401, detail="Refresh token not found")

    if token_record.is_revoked or token_record.revoked_at is not None:
        revoke_family_tokens(db, token_record.user_id, token_record.family_id)
        raise HTTPException(status_code=401, detail="Refresh token revoked")

    if token_record.replaced_by_id is not None:
        revoke_family_tokens(db, token_record.user_id, token_record.family_id)
        raise HTTPException(status_code=401, detail="Refresh token reuse detected")

    if token_record.expires_at < datetime.utcnow():
        token_record.is_revoked = True
        token_record.revoked_at = datetime.utcnow()
        db.commit()
        raise HTTPException(status_code=401, detail="Refresh token expired")

    user = db.query(User).filter(User.id == token_record.user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    new_refresh_value = create_refresh_token(user.username)
    new_record = create_refresh_record(db, user.id, new_refresh_value, token_record.family_id)
    token_record.replaced_by_id = new_record.id
    token_record.revoked_at = datetime.utcnow()
    token_record.is_revoked = True
    token_record.last_used_at = datetime.utcnow()
    db.commit()

    access_token = create_access_token(user.username)
    return {
        "access_token": access_token,
        "refresh_token": new_refresh_value,
        "token_type": "bearer",
    }


@app.post("/logout")
def logout(payload: LogoutRequest, db: Session = Depends(get_db)):
    if not payload.refresh_token:
        return {"status": "logged_out"}

    token_hash = hash_refresh_token(payload.refresh_token)
    token_record = db.query(RefreshToken).filter(RefreshToken.token_hash == token_hash).first()
    if token_record:
        revoke_family_tokens(db, token_record.user_id, token_record.family_id)
        token_record.revoked_at = datetime.utcnow()
        token_record.is_revoked = True
        db.commit()
    return {"status": "logged_out"}


@app.get("/me", response_model=UserMe)
def me(current_user: User = Depends(get_current_user)):
    return {"id": current_user.id, "username": current_user.username}
