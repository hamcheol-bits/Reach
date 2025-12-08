"""
스케줄러 관리 API 라우터
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional

from app.services.scheduler import scheduler

router = APIRouter(prefix="/scheduler", tags=["scheduler"])


@router.post("/start")
async def start_scheduler(
    korea_schedule: Optional[str] = Query(
        "0 18 * * 1-5",
        description="한국 시장 수집 스케줄 (cron 표현식)"
    ),
    us_schedule: Optional[str] = Query(
        "0 10 * * 1-5",
        description="미국 시장 수집 스케줄 (cron 표현식)"
    )
):
    """
    스케줄러 시작

    - korea_schedule: 한국 시장 cron 표현식 (기본: 월-금 오후 6시)
    - us_schedule: 미국 시장 cron 표현식 (기본: 월-금 오전 10시)

    **Cron 표현식 예시:**
    - "0 18 * * 1-5": 월-금 오후 6시
    - "0 */4 * * *": 매 4시간마다
    - "0 0 * * *": 매일 자정
    - "30 9 * * 1-5": 월-금 오전 9시 30분
    """
    try:
        if scheduler.is_running():
            return {
                "status": "info",
                "message": "Scheduler is already running",
                "jobs": scheduler.get_jobs()
            }

        scheduler.start(korea_schedule, us_schedule)

        return {
            "status": "success",
            "message": "Scheduler started successfully",
            "jobs": scheduler.get_jobs()
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error starting scheduler: {str(e)}"
        )


@router.post("/stop")
async def stop_scheduler():
    """
    스케줄러 중지

    모든 예약된 작업을 중지합니다.
    """
    try:
        if not scheduler.is_running():
            return {
                "status": "info",
                "message": "Scheduler is not running"
            }

        scheduler.stop()

        return {
            "status": "success",
            "message": "Scheduler stopped successfully"
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error stopping scheduler: {str(e)}"
        )


@router.get("/status")
async def get_scheduler_status():
    """
    스케줄러 상태 조회

    현재 스케줄러 실행 여부와 등록된 작업 목록을 반환합니다.
    """
    try:
        return {
            "status": "success",
            "is_running": scheduler.is_running(),
            "jobs": scheduler.get_jobs() if scheduler.is_running() else []
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error getting scheduler status: {str(e)}"
        )


@router.post("/run/korea")
async def run_korea_collection_now():
    """
    한국 시장 수집 즉시 실행

    스케줄과 무관하게 한국 시장 데이터를 즉시 수집합니다.
    (증분 업데이트로 실행)
    """
    try:
        scheduler.collect_korea_daily()

        return {
            "status": "success",
            "message": "Korea market collection executed successfully"
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error executing Korea collection: {str(e)}"
        )


@router.post("/run/us")
async def run_us_collection_now():
    """
    미국 시장 수집 즉시 실행

    스케줄과 무관하게 미국 시장 데이터를 즉시 수집합니다.
    (증분 업데이트로 실행)
    """
    try:
        scheduler.collect_us_daily()

        return {
            "status": "success",
            "message": "US market collection executed successfully"
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error executing US collection: {str(e)}"
        )