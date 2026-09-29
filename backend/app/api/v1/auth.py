from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.api import deps
from app.core.security import create_access_token, revoke_token, verify_password
from app.models.user import User
from app.schemas.auth import LoginRequest, Token
from app.schemas.user import UserOut

router = APIRouter(prefix="/auth", tags=["认证"])


@router.post("/login", response_model=Token, summary="用户登录")
def login(body: LoginRequest, db: Session = Depends(deps.get_db)):
    user = db.scalar(deps.USER_QUERY.filter(User.username == body.username))
    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="账号已被禁用")
    token = create_access_token(subject=str(user.id))
    return Token(access_token=token)


@router.get("/me", response_model=UserOut, summary="当前登录用户信息")
def get_me(current_user: User = Depends(deps.get_current_user)):
    return current_user


@router.post("/logout", summary="登出并使当前令牌立即失效")
def logout(
    current_user: User = Depends(deps.get_current_user),
    credentials: HTTPAuthorizationCredentials = Depends(deps.get_current_credentials),
    db: Session = Depends(deps.get_db),
):
    """把当前 token 的 jti 登记到撤销名单，之后携带该 token 的请求一律 401。"""
    revoke_token(db, credentials.credentials, current_user.id)
    return {"ok": True}
