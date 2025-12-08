from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.config import get_settings
from app.database import get_db

router = APIRouter(prefix="/health", tags=["health"])
settings = get_settings()


@router.get("")
async def health_check():
    """서비스 헬스 체크"""
    return {
        "status": "healthy",
        "service": settings.app_name,
        "version": settings.app_version
    }


@router.get("/db")
async def database_health_check(db: Session = Depends(get_db)):
    """데이터베이스 연결 체크"""
    try:
        db.execute(text("SELECT 1"))
        return {
            "status": "healthy",
            "database": "connected"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "database": "disconnected",
            "error": str(e)
        }