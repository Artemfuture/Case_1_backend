from fastapi import APIRouter

from app.api.routes.checks import router as checks_router


api_router = APIRouter(prefix="/api")
api_router.include_router(checks_router)