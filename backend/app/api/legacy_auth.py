import os

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlmodel import Session, SQLModel, select

from app.auth import (
    authenticate,
    decode_and_validate_token,
    get_current_admin_user,
    get_current_user,
    get_jwt_secret,
    issue_token,
)
from app.db import get_engine
from app.models import User
from app.security import hash_password, verify_password

router = APIRouter()

class LoginRequest(SQLModel):
    username: str
    password: str


class LoginResponse(SQLModel):
    access_token: str
    token_type: str = "bearer"
    refresh_token: str


class RegisterRequest(SQLModel):
    username: str
    password: str
    role: str = "user"


class RefreshRequest(SQLModel):
    refresh_token: str

@router.post("/auth/login", response_model=LoginResponse, tags=["auth"])
def login(payload: LoginRequest) -> LoginResponse:
    user = authenticate(payload.username, payload.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    secret = get_jwt_secret()
    # V45: 延长 access token 有效期到 7 天（604800秒），refresh token 30 天
    access = issue_token(user, secret=secret, exp_seconds=int(os.getenv("JWT_EXPIRES_IN", "604800")), token_type="access")
    refresh = issue_token(
        user, secret=secret, exp_seconds=int(os.getenv("JWT_REFRESH_EXPIRES_IN", "2592000")), token_type="refresh"
    )
    return LoginResponse(access_token=access, refresh_token=refresh)


@router.post("/auth/register", response_model=LoginResponse, tags=["auth"])
def register(
    payload: RegisterRequest,
    _admin_user_id: int = Depends(get_current_admin_user),
) -> LoginResponse:
    engine = get_engine()
    with Session(engine) as session:
        exists = session.exec(select(User).where(User.username == payload.username)).first()
        if exists:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already exists")
        user = User(username=payload.username, password_hash=hash_password(payload.password), role=payload.role)
        session.add(user)
        session.commit()
        session.refresh(user)
        secret = get_jwt_secret()
        # V45: 延长 access token 有效期到 7 天（604800秒），refresh token 30 天
        access = issue_token(user, secret=secret, exp_seconds=int(os.getenv("JWT_EXPIRES_IN", "604800")), token_type="access")
        refresh = issue_token(
            user, secret=secret, exp_seconds=int(os.getenv("JWT_REFRESH_EXPIRES_IN", "2592000")), token_type="refresh"
        )
        return LoginResponse(access_token=access, refresh_token=refresh)


@router.post("/auth/refresh", response_model=LoginResponse, tags=["auth"])
def refresh(payload: RefreshRequest) -> LoginResponse:
    secret = get_jwt_secret()
    data = decode_and_validate_token(payload.refresh_token, secret=secret, expected_type="refresh")
    engine = get_engine()
    with Session(engine) as session:
        user = session.exec(select(User).where(User.id == data.get("sub"))).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
        # V45: 延长 access token 有效期到 7 天（604800秒），refresh token 30 天
        access = issue_token(user, secret=secret, exp_seconds=int(os.getenv("JWT_EXPIRES_IN", "604800")), token_type="access")
        refresh_token = issue_token(
            user, secret=secret, exp_seconds=int(os.getenv("JWT_REFRESH_EXPIRES_IN", "2592000")), token_type="refresh"
        )
        return LoginResponse(access_token=access, refresh_token=refresh_token)


class ChangePasswordRequest(SQLModel):
    current_password: str
    new_password: str


class UpdateUsernameRequest(BaseModel):
    new_username: str


@router.post("/api/auth/update-username", tags=["auth"])
def update_username(
    payload: UpdateUsernameRequest,
    user_id: int = Depends(get_current_user),
):
    """修改用户名（显示名称）"""
    new_username = payload.new_username.strip()
    if not new_username:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="用户名不能为空")
    if len(new_username) > 50:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="用户名长度不能超过50个字符")

    engine = get_engine()
    with Session(engine) as session:
        user = session.exec(select(User).where(User.id == user_id)).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        # 更新用户名
        user.username = new_username
        session.add(user)
        session.commit()
        session.refresh(user)

        return {"message": "用户名修改成功", "username": user.username}


@router.post("/auth/change-password", tags=["auth"])
def change_password(
    payload: ChangePasswordRequest,
    user_id: int = Depends(get_current_user),
):
    """修改用户密码"""
    engine = get_engine()
    with Session(engine) as session:
        user = session.exec(select(User).where(User.id == user_id)).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        # 验证当前密码
        if not verify_password(payload.current_password, user.password_hash):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="当前密码不正确")

        # 更新密码
        user.password_hash = hash_password(payload.new_password)
        session.add(user)
        session.commit()

        return {"message": "密码修改成功"}


# ---- AI Token 更新 API ----
class UpdateTokenRequest(BaseModel):
    token: str
    expires: str | None = None  # 兼容旧前端字段，DeepSeek Token 不再依赖本地过期时间


@router.post("/api/settings/update-token", tags=["settings"])
def update_api_token(
    payload: UpdateTokenRequest,
    user_id: int = Depends(get_current_user),
):
    """更新 DeepSeek API Token."""
    new_token = payload.token.strip()
    if not new_token:
        raise HTTPException(status_code=400, detail="Token 不能为空")

    if len(new_token) < 20:
        raise HTTPException(status_code=400, detail="Token 格式不正确")

    try:
        os.environ["AI_API_KEY"] = new_token
        os.environ["AI_API_BASE"] = "https://api.deepseek.com"
        os.environ["AI_MODEL"] = "deepseek-v4-pro"

        env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")

        if os.path.exists(env_path):
            with open(env_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            key_found = False
            base_found = False
            model_found = False
            new_lines = []

            for line in lines:
                if line.startswith("AI_API_KEY="):
                    new_lines.append(f"AI_API_KEY={new_token}\n")
                    key_found = True
                elif line.startswith("AI_API_BASE="):
                    new_lines.append("AI_API_BASE=https://api.deepseek.com\n")
                    base_found = True
                elif line.startswith("AI_MODEL="):
                    new_lines.append("AI_MODEL=deepseek-v4-pro\n")
                    model_found = True
                elif line.startswith("AI_FALLBACK_MODELS_SIMPLE="):
                    # DeepSeek 单模型模式下不再写回备用模型配置
                    continue
                else:
                    new_lines.append(line)

            if not key_found:
                new_lines.append(f"\nAI_API_KEY={new_token}\n")
            if not base_found:
                new_lines.append("AI_API_BASE=https://api.deepseek.com\n")
            if not model_found:
                new_lines.append("AI_MODEL=deepseek-v4-pro\n")

            with open(env_path, 'w', encoding='utf-8') as f:
                f.writelines(new_lines)
        else:
            with open(env_path, 'w', encoding='utf-8') as f:
                f.write("# DeepSeek API 配置\n")
                f.write(f"AI_API_KEY={new_token}\n")
                f.write("AI_API_BASE=https://api.deepseek.com\n")
                f.write("AI_MODEL=deepseek-v4-pro\n")

        return {
            "message": "DeepSeek Token 更新成功",
            "model": "deepseek-v4-pro"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Token 更新失败: {str(e)}")
