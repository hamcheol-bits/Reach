from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.config import get_settings
from app.routers import health, stock, korea, us, batch, scheduler as scheduler_router, financial
from app.services.scheduler import scheduler

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """앱 생명주기 관리"""
    # 시작 시
    print("🚀 Starting Reach - Financial Data Collection Service")

    # 스케줄러 자동 시작 (선택적)
    if settings.enable_scheduler:
        print("📅 Starting scheduler...")
        scheduler.start()

    yield

    # 종료 시
    print("🛑 Shutting down...")
    if scheduler.is_running():
        scheduler.stop()


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Financial Data Collection Service for Korean and US Markets",
    lifespan=lifespan
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(health.router)
app.include_router(stock.router, prefix="/api/v1")
app.include_router(korea.router, prefix="/api/v1")
app.include_router(us.router, prefix="/api/v1")
app.include_router(batch.router, prefix="/api/v1")  # 배치 수집 라우터
app.include_router(scheduler_router.router, prefix="/api/v1")  # 스케줄러 라우터
app.include_router(financial.router, prefix="/api/v1")


@app.get("/")
async def root():
    return {
        "service": settings.app_name,
        "version": settings.app_version,
        "status": "running"
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=settings.app_port)