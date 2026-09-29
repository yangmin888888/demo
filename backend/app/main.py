from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import audit, auth, users
from app.api.v1.router import router as api_router
from app.core.config import settings
from app.db.session import SessionLocal
from app.services.audit_service import install_audit_listeners

api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(audit.router)

install_audit_listeners()


@asynccontextmanager
async def lifespan(_: FastAPI):
    from app.db.init_db import init_db

    db = SessionLocal()
    try:
        init_db(db)
    finally:
        db.close()
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        description="通用后台管理 API",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router, prefix="/api/v1")

    @app.get("/", tags=["健康检查"])
    def root():
        return {"app": settings.app_name, "status": "ok"}

    return app


app = create_app()
