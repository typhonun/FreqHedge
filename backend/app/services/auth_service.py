# backend/app/services/auth_service.py
import secrets
from datetime import datetime, timedelta
from typing import Optional

from passlib.context import CryptContext
from jose import jwt, JWTError
from sqlalchemy.orm import Session

from config.settings import (
    SECRET_KEY, ALGORITHM,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    RESET_TOKEN_EXPIRE_MINUTES,
)
from app.models.user import User

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


class AuthService:

    # ---------- 密码 ----------
    @staticmethod
    def hash_password(pw: str) -> str:
        return pwd_context.hash(pw)

    @staticmethod
    def verify_password(pw: str, hashed: str) -> bool:
        try:
            return pwd_context.verify(pw, hashed)
        except Exception:
            return False

    # ---------- JWT ----------
    @staticmethod
    def create_access_token(user_id: int, email: str) -> str:
        exp = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        payload = {"sub": str(user_id), "email": email, "exp": exp}
        return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

    @staticmethod
    def decode_token(token: str) -> Optional[dict]:
        try:
            return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        except JWTError:
            return None

    # ---------- 用户 ----------
    @staticmethod
    def get_by_email(db: Session, email: str) -> Optional[User]:
        return db.query(User).filter(User.email == email.lower()).first()

    @staticmethod
    def get_by_id(db: Session, uid: int) -> Optional[User]:
        return db.query(User).filter(User.id == uid).first()

    @staticmethod
    def create_user(db: Session, email: str, password: str, nickname: str = "") -> User:
        user = User(
            email=email.lower(),
            nickname=nickname or email.split("@")[0],
            password_hash=AuthService.hash_password(password),
            verify_token=secrets.token_urlsafe(32),
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    # ---------- 重置密码 token ----------
    @staticmethod
    def gen_reset_token(db: Session, user: User) -> str:
        token = secrets.token_urlsafe(32)
        user.reset_token = token
        user.reset_token_expire = datetime.utcnow() + timedelta(minutes=RESET_TOKEN_EXPIRE_MINUTES)
        db.commit()
        return token

    @staticmethod
    def consume_reset_token(db: Session, token: str, new_password: str) -> bool:
        user = db.query(User).filter(User.reset_token == token).first()
        if not user:
            return False
        if not user.reset_token_expire or user.reset_token_expire < datetime.utcnow():
            return False
        user.password_hash = AuthService.hash_password(new_password)
        user.reset_token = None
        user.reset_token_expire = None
        db.commit()
        return True

    @staticmethod
    def update_nickname(db: Session, user: User, nickname: str) -> User:
        user.nickname = nickname.strip()[:32]
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def change_password(db: Session, user: User, old_password: str, new_password: str) -> bool:
        # 验证旧密码
        if not AuthService.verify_password(old_password, user.password_hash):
            return False
        # 更新为新密码
        user.password_hash = AuthService.hash_password(new_password)
        db.commit()
        return True