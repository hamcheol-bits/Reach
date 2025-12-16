from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import health, stock, korea, batch, financial, pykrx_debug, data_quality, screening

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Korean Stock Market Data Collection & Screening Service",
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
app.include_router(batch.router, prefix="/api/v1")
app.include_router(financial.router, prefix="/api/v1")
app.include_router(pykrx_debug.router, prefix="/api/v1")
app.include_router(data_quality.router, prefix="/api/v1")
app.include_router(screening.router, prefix="/api/v1")  # 종목 스크리닝 API


@app.get("/")
async def root():
    return {
        "service": settings.app_name,
        "version": settings.app_version,
        "status": "running",
        "markets": ["KOSPI", "KOSDAQ"]
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=settings.app_port)