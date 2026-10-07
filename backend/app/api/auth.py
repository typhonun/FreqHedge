# backend/app/api/auth.py
import secrets
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session
from config.settings import DEV_MODE, FRONTEND_URL
from app.db import get_db
from app.services.auth_service import AuthService
from app.services.mail_service import MailService
from typing import Optional

router = APIRouter()
security = HTTPBearer(auto_error=False)


# ================= Schemas =================
class UpdateProfileIn(BaseModel):
    nickname: str = Field(min_length=1, max_length=32)


class ChangePasswordIn(BaseModel):
    old_password: str = Field(min_length=1)
    new_password: str = Field(min_length=8, max_length=64)


class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=64)
    nickname: str = Field(default="", max_length=32)


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class ForgotIn(BaseModel):
    email: EmailStr


class ResetIn(BaseModel):
    token: str
    new_password: str = Field(min_length=8, max_length=64)


class UserOut(BaseModel):
    id: int
    email: str
    nickname: str
    is_verified: bool = False
    created_at: Optional[str] = None


# ================= 依赖 =================
def get_current_user(
    creds: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    if not creds:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")
    payload = AuthService.decode_token(creds.credentials)
    if not payload:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token")
    user = AuthService.get_by_id(db, int(payload["sub"]))
    if not user or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found")
    return user


# ================= 路由 =================
@router.post("/register")
async def register(body: RegisterIn, db: Session = Depends(get_db)):
    if AuthService.get_by_email(db, body.email):
        raise HTTPException(400, "该邮箱已被注册")
    user = AuthService.create_user(db, body.email, body.password, body.nickname)

    # ★ 开发模式：不发邮件
    if not DEV_MODE:
        try:
            await MailService.send_verify_email(user.email, user.verify_token)
        except Exception as e:
            print(f"[auth] send verify mail failed: {e}")

    token = AuthService.create_access_token(user.id, user.email)
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "nickname": user.nickname,
            "is_verified": user.is_verified,
            "created_at": user.created_at.isoformat() if user.created_at else None,
        },
    }


@router.post("/login")
def login(body: LoginIn, db: Session = Depends(get_db)):
    user = AuthService.get_by_email(db, body.email)
    if not user or not AuthService.verify_password(body.password, user.password_hash):
        raise HTTPException(401, "邮箱或密码错误")
    if not user.is_active:
        raise HTTPException(403, "账号已被禁用")

    user.last_login = datetime.utcnow()
    db.commit()

    token = AuthService.create_access_token(user.id, user.email)
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "nickname": user.nickname,
            "is_verified": user.is_verified,
            "created_at": user.created_at.isoformat() if user.created_at else None,
        },
    }


@router.get("/me", response_model=UserOut)
def me(user=Depends(get_current_user)):
    return {
        "id": user.id,
        "email": user.email,
        "nickname": user.nickname,
        "is_verified": user.is_verified,
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }


@router.put("/profile", response_model=UserOut)
def update_profile(
    body: UpdateProfileIn,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user = AuthService.update_nickname(db, user, body.nickname)
    return {
        "id": user.id,
        "email": user.email,
        "nickname": user.nickname,
        "is_verified": user.is_verified,
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }


@router.post("/change-password")
def change_password(
    body: ChangePasswordIn,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """修改当前用户的密码"""
    ok = AuthService.change_password(db, user, body.old_password, body.new_password)
    if not ok:
        raise HTTPException(400, "原密码错误")
    return {"success": True, "message": "密码修改成功"}


@router.post("/logout")
def logout():
    return {"success": True}


@router.post("/forgot")
async def forgot(body: ForgotIn, db: Session = Depends(get_db)):
    user = AuthService.get_by_email(db, body.email)

    # 用户不存在：仍然返回成功，防止枚举邮箱
    if not user:
        return {"success": True, "message": "如果邮箱存在，重置链接已发送"}

    # 生成 token（无论开发/生产都要生成）
    token = AuthService.gen_reset_token(db, user)
    reset_url = f"{FRONTEND_URL}/reset-password?token={token}"

    # ★ 开发模式：不真的发邮件，直接把链接返回
    if DEV_MODE:
        print(f"[DEV] 重置链接 for {user.email}: {reset_url}")
        return {
            "success": True,
            "dev_mode": True,
            "dev_reset_url": reset_url,
            "message": "开发模式：重置链接已生成",
        }

    # 生产模式：发邮件
    try:
        await MailService.send_reset_email(user.email, token)
    except Exception as e:
        print(f"[auth] send reset mail failed: {e}")

    return {"success": True, "message": "如果邮箱存在，重置链接已发送"}


@router.post("/reset")
def reset(body: ResetIn, db: Session = Depends(get_db)):
    ok = AuthService.consume_reset_token(db, body.token, body.new_password)
    if not ok:
        raise HTTPException(400, "重置链接无效或已过期")
    return {"success": True}


@router.post("/send-verify")
async def send_verify(
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """重新发送验证邮件"""
    if user.is_verified:
        return {"success": True, "message": "邮箱已验证"}

    # 生成新 token（防止旧 token 泄漏）
    user.verify_token = secrets.token_urlsafe(32)
    db.commit()

    try:
        await MailService.send_verify_email(user.email, user.verify_token)
    except Exception as e:
        print(f"[auth] send verify mail failed: {e}")
        raise HTTPException(500, "邮件发送失败，请稍后重试")

    return {"success": True, "message": "验证邮件已发送"}