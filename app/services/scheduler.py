"""
데이터 수집 스케줄러

APScheduler를 사용하여 정기적으로 데이터 수집 작업 실행
"""
from datetime import datetime
from typing import Optional
import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.database import SessionLocal
from app.services.batch_collector import BatchCollector

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DataCollectionScheduler:
    """데이터 수집 스케줄러"""

    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.collector = BatchCollector()
        self._is_running = False

    def collect_korea_daily(self):
        """한국 시장 일일 수집 작업"""
        logger.info("="*60)
        logger.info("🕐 Starting scheduled Korea market collection")
        logger.info(f"   Time: {datetime.now().isoformat()}")
        logger.info("="*60)

        db = SessionLocal()
        try:
            # KOSPI 수집 (증분)
            result_kospi = self.collector.collect_korea_batch(
                db, market='KOSPI', incremental=True
            )
            logger.info(f"✅ KOSPI collection completed: {result_kospi['stocks_success']} stocks")

            # KOSDAQ 수집 (증분)
            result_kosdaq = self.collector.collect_korea_batch(
                db, market='KOSDAQ', incremental=True
            )
            logger.info(f"✅ KOSDAQ collection completed: {result_kosdaq['stocks_success']} stocks")

        except Exception as e:
            logger.error(f"❌ Error in scheduled Korea collection: {e}")
        finally:
            db.close()

        logger.info("="*60)
        logger.info("🏁 Scheduled Korea market collection finished")
        logger.info("="*60 + "\n")

    def collect_us_daily(self):
        """미국 시장 일일 수집 작업"""
        logger.info("="*60)
        logger.info("🕐 Starting scheduled US market collection")
        logger.info(f"   Time: {datetime.now().isoformat()}")
        logger.info("="*60)

        db = SessionLocal()
        try:
            # S&P 500 샘플 수집 (증분)
            result = self.collector.collect_us_batch(
                db,
                tickers=self.collector.us_collector.sp500_sample,
                incremental=True
            )
            logger.info(f"✅ US market collection completed: {result['stocks_success']} stocks")

        except Exception as e:
            logger.error(f"❌ Error in scheduled US collection: {e}")
        finally:
            db.close()

        logger.info("="*60)
        logger.info("🏁 Scheduled US market collection finished")
        logger.info("="*60 + "\n")

    def start(
        self,
        korea_schedule: str = "0 18 * * 1-5",  # 월-금 오후 6시 (KST)
        us_schedule: str = "0 10 * * 1-5"      # 월-금 오전 10시 (KST, 미 동부 전날 저녁 9시)
    ):
        """
        스케줄러 시작

        Args:
            korea_schedule: 한국 시장 수집 스케줄 (cron 표현식)
                기본값: "0 18 * * 1-5" (월-금 오후 6시, 장 마감 후)
            us_schedule: 미국 시장 수집 스케줄 (cron 표현식)
                기본값: "0 10 * * 1-5" (월-금 오전 10시, 미 동부 시간 전날 저녁)

        Cron 표현식 형식: "초 분 시 일 월 요일"
        예시:
        - "0 18 * * 1-5": 월-금 오후 6시
        - "0 */4 * * *": 매 4시간마다
        - "0 0 * * *": 매일 자정
        """
        if self._is_running:
            logger.warning("⚠️  Scheduler is already running")
            return

        # 한국 시장 수집 작업 추가
        self.scheduler.add_job(
            self.collect_korea_daily,
            trigger=CronTrigger.from_crontab(korea_schedule),
            id='korea_market_collection',
            name='Korea Market Daily Collection',
            replace_existing=True
        )
        logger.info(f"📅 Korea market collection scheduled: {korea_schedule}")

        # 미국 시장 수집 작업 추가
        self.scheduler.add_job(
            self.collect_us_daily,
            trigger=CronTrigger.from_crontab(us_schedule),
            id='us_market_collection',
            name='US Market Daily Collection',
            replace_existing=True
        )
        logger.info(f"📅 US market collection scheduled: {us_schedule}")

        # 스케줄러 시작
        self.scheduler.start()
        self._is_running = True

        logger.info("="*60)
        logger.info("✅ Scheduler started successfully!")
        logger.info("="*60)
        logger.info("Scheduled jobs:")
        for job in self.scheduler.get_jobs():
            logger.info(f"  - {job.name}")
            logger.info(f"    Next run: {job.next_run_time}")
        logger.info("="*60 + "\n")

    def stop(self):
        """스케줄러 중지"""
        if not self._is_running:
            logger.warning("⚠️  Scheduler is not running")
            return

        self.scheduler.shutdown()
        self._is_running = False
        logger.info("🛑 Scheduler stopped")

    def get_jobs(self):
        """현재 등록된 작업 목록 조회"""
        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append({
                'id': job.id,
                'name': job.name,
                'next_run_time': job.next_run_time.isoformat() if job.next_run_time else None,
                'trigger': str(job.trigger)
            })
        return jobs

    def is_running(self):
        """스케줄러 실행 여부"""
        return self._is_running


# 글로벌 스케줄러 인스턴스
scheduler = DataCollectionScheduler()