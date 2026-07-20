from fastapi import APIRouter

from app.api.v1.admin import router as admin_router
from app.api.v1.admin_content import router as admin_content_router
from app.api.v1.auth import router as auth_router
from app.api.v1.games import router as games_router
from app.api.v1.learn import router as learn_router
from app.api.v1.users import router as users_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(learn_router)
api_router.include_router(games_router)
api_router.include_router(admin_router)
api_router.include_router(admin_content_router)
