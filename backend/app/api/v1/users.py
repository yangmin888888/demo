from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api import deps
from app.models.user import User
from app.schemas.user import PageResult, UserCreate, UserOut, UserUpdate
from app.services import user_service

router = APIRouter(prefix="/users", tags=["用户管理"])


@router.get("", response_model=PageResult, summary="用户列表")
def list_users(
    db: Session = Depends(deps.get_db),
    _: User = Depends(deps.get_current_superuser),
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    keyword: str | None = Query(None, description="用户名/昵称/邮箱模糊搜索"),
):
    query = select(User)
    if keyword:
        pattern = f"%{keyword}%"
        query = query.where(or_(User.username.like(pattern), User.nickname.like(pattern), User.email.like(pattern)))
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    items = db.scalars(query.order_by(User.id.desc()).offset((page - 1) * size).limit(size)).all()
    return PageResult(total=total, items=items)


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED, summary="创建用户")
def create_user(
    body: UserCreate,
    db: Session = Depends(deps.get_db),
    _: User = Depends(deps.get_current_superuser),
):
    if user_service.get_by_username(db, body.username):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="用户名已存在")
    if user_service.get_by_email(db, body.email):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="邮箱已被使用")
    user = user_service.create(db, body)
    return user


@router.get("/{user_id}", response_model=UserOut, summary="用户详情")
def get_user(
    user_id: int,
    db: Session = Depends(deps.get_db),
    _: User = Depends(deps.get_current_superuser),
):
    user = user_service.get_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")
    return user


@router.put("/{user_id}", response_model=UserOut, summary="更新用户")
def update_user(
    user_id: int,
    body: UserUpdate,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_superuser),
):
    user = user_service.get_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")

    data = body.model_dump(exclude_unset=True)
    if "email" in data:
        exists = user_service.get_by_email(db, data["email"])
        if exists and exists.id != user_id:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="邮箱已被使用")
    if user_id == current_user.id:
        if data.get("is_superuser") is False or data.get("is_active") is False:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="不能取消自身的管理员/启用状态")
    return user_service.update(db, user, data)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT, summary="删除用户")
def delete_user(
    user_id: int,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_superuser),
):
    user = user_service.get_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")
    if user.id == current_user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="不能删除当前登录账号")
    user_service.delete(db, user)
