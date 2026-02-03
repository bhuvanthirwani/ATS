from fastapi import APIRouter
from src.api.v1.endpoints import files, actions, auth

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(files.router, prefix="/files", tags=["files"])
api_router.include_router(actions.router, prefix="/actions", tags=["Actions"])
