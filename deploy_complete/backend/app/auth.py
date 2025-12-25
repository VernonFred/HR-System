import base64
import hmac
import json
import os
import time
from hashlib import sha256
from typing import Optional

from fastapi import Header, HTTPException, status
from sqlmodel import Session, select

from app.models import User
from app.security import encode_jwt, hash_password, verify_password
from app.db import get_engine


def _b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def _decode_jwt(token: str, secret: str) -> dict:
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        header_b64, payload_b64, sig_b64 = token.split(".")
    except ValueError:
        logger.warning("[AUTH] Malformed token - cannot split into 3 parts")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Malformed token")

    try:
        header = json.loads(_b64url_decode(header_b64))
        payload = json.loads(_b64url_decode(payload_b64))
    except Exception as e:
        logger.warning(f"[AUTH] Invalid token payload: {e}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")

    if header.get("alg") != "HS256":
        logger.warning(f"[AUTH] Unsupported alg: {header.get('alg')}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unsupported alg")

    signing_input = f"{header_b64}.{payload_b64}".encode()
    expected_sig = hmac.new(secret.encode(), signing_input, sha256).digest()
    try:
        sig = _b64url_decode(sig_b64)
    except Exception as e:
        logger.warning(f"[AUTH] Invalid token signature format: {e}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token signature")

    if not hmac.compare_digest(sig, expected_sig):
        logger.warning("[AUTH] Signature mismatch")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Signature mismatch")

    exp = payload.get("exp")
    if exp and time.time() > exp:
        logger.warning(f"[AUTH] Token expired at {exp}, current time: {time.time()}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")

    return payload


def get_default_user_credentials() -> tuple[str, str]:
    username = os.getenv("AUTH_USERNAME", "admin")
    password = os.getenv("AUTH_PASSWORD", "admin123")
    return username, password


def get_or_create_default_user() -> User:
    """
    确保系统中存在至少一个管理员用户。
    - 如果已有任何管理员用户，直接返回（不创建新用户）
    - 如果没有管理员用户，创建默认管理员账号
    """
    engine = get_engine()
    with Session(engine) as session:
        # 检查是否存在任何管理员用户
        admin_user = session.exec(select(User).where(User.role == "admin")).first()
        if admin_user:
            return admin_user  # 已有管理员，不创建新用户
        
        # 没有管理员时，才创建默认用户
        username, password = get_default_user_credentials()
        user = User(username=username, password_hash=hash_password(password), role="admin")
        session.add(user)
        session.commit()
        session.refresh(user)
        return user


def authenticate(username: str, password: str) -> Optional[User]:
    engine = get_engine()
    with Session(engine) as session:
        user = session.exec(select(User).where(User.username == username)).first()
        if user and verify_password(password, user.password_hash):
            return user
    return None


def issue_token(user: User, *, secret: str, exp_seconds: int, token_type: str = "access") -> str:
    payload = {"sub": user.id, "username": user.username, "role": user.role, "type": token_type}
    return encode_jwt(payload, secret, exp_seconds=exp_seconds)


def decode_and_validate_token(token: str, secret: str, expected_type: str = "access") -> dict:
    payload = _decode_jwt(token, secret)
    t = payload.get("type", "access")
    if t != expected_type:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")
    return payload


def get_current_user(
    authorization: Optional[str] = Header(default=None),
    x_user_id: Optional[str] = Header(default=None),
) -> int:
    """
    JWT/占位鉴权：
    - 优先使用 Authorization: Bearer <jwt>（HS256，secret 来自 JWT_SECRET）
    - 兼容自定义头 X-User-Id 作为降级（无签名校验）
    """
    import logging
    logger = logging.getLogger(__name__)
    
    secret = os.getenv("JWT_SECRET", "change_me")

    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
        logger.info(f"[AUTH] Validating token (first 20 chars): {token[:20]}...")
        payload = _decode_jwt(token, secret)
        sub = payload.get("sub")
        if sub is None:
            logger.warning("[AUTH] Missing sub in token")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing sub in token")
        try:
            logger.info(f"[AUTH] Token valid, user_id: {sub}")
            return int(sub)
        except (TypeError, ValueError):
            logger.warning(f"[AUTH] Invalid sub in token: {sub}")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid sub in token")

    if x_user_id:
        try:
            return int(x_user_id.strip())
        except ValueError:
            logger.warning(f"[AUTH] Invalid X-User-Id: {x_user_id}")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid X-User-Id")

    logger.warning(f"[AUTH] Missing Authorization header. Got: {authorization}")
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing Authorization/X-User-Id")
