import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.revoked_token import RevokedToken


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except ValueError:
        return False


def create_access_token(subject: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    # jti 是每个 token 的唯一标识，登出时据此把 token 加入撤销名单
    payload = {"sub": subject, "exp": expire, "type": "access", "jti": uuid.uuid4().hex}
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def decode_access_token(token: str) -> dict | None:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        if payload.get("type") != "access":
            return None
        return payload
    except jwt.PyJWTError:
        return None


def is_token_revoked(db: Session, jti: str | None) -> bool:
    if not jti:
        return False
    return db.scalar(select(RevokedToken.jti).where(RevokedToken.jti == jti)) is not None


def revoke_token(db: Session, token: str, user_id: int | None) -> bool:
    """把 token 加入撤销名单。返回是否成功撤销（token 无法解析时为 False）。"""
    payload = decode_access_token(token)
    jti = payload.get("jti") if payload else None
    if not jti:
        return False
    if db.scalar(select(RevokedToken.jti).where(RevokedToken.jti == jti)):
        return True
    # 项目内 DateTime 一律为 naive（见 README 技术债），此处统一存 UTC 无时区值
    expires_at = datetime.fromtimestamp(payload["exp"], tz=timezone.utc).replace(tzinfo=None)
    db.add(RevokedToken(jti=jti, user_id=user_id, expires_at=expires_at))
    db.commit()
    return True


def purge_expired_revocations(db: Session) -> int:
    """清理已自然过期的撤销记录，避免 revoked_tokens 表无限增长。"""
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    result = db.execute(delete(RevokedToken).where(RevokedToken.expires_at < now))
    db.commit()
    return result.rowcount or 0
