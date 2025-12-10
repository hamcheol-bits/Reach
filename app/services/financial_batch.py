"""
배치 재무제표 수집 서비스

주요 종목의 재무제표를 일괄 수집합니다.
"""
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import time

from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from app.models import Stock, StockMarketData, FinancialStatement
from app.services.dart_api import DartApiService


class FinancialBatchCollector:
    """재무제표 배치 수집"""

    def __init__(self):
        self.dart_service = DartApiService()

    def get_all_kr_stocks(
        self,
        db: Session,
        market: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[str]:
        """
        한국 주식 전체 조회

        Args:
            db: 데이터베이스 세션
            market: KOSPI 또는 KOSDAQ (None이면 전체)
            limit: 조회할 종목 수 제한

        Returns:
            종목코드 리스트
        """
        query = db.query(Stock.ticker).filter(Stock.country == 'KR')

        if market:
            query = query.filter(Stock.market == market.upper())

        if limit:
            query = query.limit(limit)

        stocks = query.all()
        return [ticker for (ticker,) in stocks]

    def get_latest_financial_year(
        self,
        db: Session,
        stock_id: int
    ) -> Optional[int]:
        """
        종목의 최신 재무제표 연도 조회

        Args:
            db: 데이터베이스 세션
            stock_id: 종목 ID

        Returns:
            최신 연도 (없으면 None)
        """
        latest = (
            db.query(func.max(FinancialStatement.fiscal_year))
            .filter(
                FinancialStatement.stock_id == stock_id,
                FinancialStatement.fiscal_quarter.is_(None)  # 연간만
            )
            .scalar()
        )
        return latest

    def collect_batch(
        self,
        db: Session,
        tickers: List[str],
        start_year: int,
        end_year: int,
        skip_existing: bool = True,
        incremental: bool = False
    ) -> Dict:
        """
        여러 종목의 재무제표 배치 수집

        Args:
            db: 데이터베이스 세션
            tickers: 종목코드 리스트
            start_year: 시작 연도
            end_year: 종료 연도
            skip_existing: 이미 수집된 데이터 건너뛰기
            incremental: 증분 모드 (True면 각 종목의 최신 연도부터만 수집)

        Returns:
            수집 결과 딕셔너리
        """
        print(f"\n{'='*60}")
        print(f"🚀 Starting Financial Batch Collection")
        print(f"   Stocks: {len(tickers)}")
        print(f"   Years: {start_year}-{end_year}")
        print(f"   Skip existing: {skip_existing}")
        print(f"   Incremental mode: {incremental}")
        print(f"{'='*60}\n")

        start_time = datetime.now()
        results = {
            'start_time': start_time.isoformat(),
            'total_stocks': len(tickers),
            'total_years': end_year - start_year + 1,
            'stocks_processed': 0,
            'stocks_success': 0,
            'stocks_failed': 0,
            'stocks_skipped': 0,
            'statements_collected': 0,
            'statements_skipped': 0,
            'errors': []
        }

        for idx, ticker in enumerate(tickers, 1):
            results['stocks_processed'] += 1
            stock_success = False
            stock_skipped = True  # 하나라도 수집하면 False

            try:
                # 종목 정보 조회
                stock = db.query(Stock).filter(Stock.ticker == ticker).first()
                if not stock:
                    error_msg = f"Stock {ticker} not found in database"
                    print(f"[{idx}/{len(tickers)}] ⚠️  {error_msg}")
                    results['errors'].append(error_msg)
                    results['stocks_failed'] += 1
                    continue

                print(f"\n[{idx}/{len(tickers)}] 📊 {ticker} ({stock.name})")
                print(f"{'─'*60}")

                # 증분 모드: 최신 연도 확인
                actual_start_year = start_year
                if incremental:
                    latest_year = self.get_latest_financial_year(db, stock.id)
                    if latest_year:
                        actual_start_year = latest_year + 1
                        if actual_start_year > end_year:
                            print(f"  ⏭️  Already up-to-date (latest: {latest_year})")
                            results['stocks_skipped'] += 1
                            continue
                        print(f"  📅 Latest: {latest_year}, collecting from {actual_start_year}")

                # 각 연도별 수집
                for year in range(actual_start_year, end_year + 1):
                    try:
                        # 이미 수집된 데이터 확인
                        if skip_existing:
                            existing = db.query(FinancialStatement).filter(
                                FinancialStatement.stock_id == stock.id,
                                FinancialStatement.fiscal_year == year,
                                FinancialStatement.fiscal_quarter.is_(None)
                            ).first()

                            if existing:
                                print(f"  {year}: ⏭️  Skipped (already exists)")
                                results['statements_skipped'] += 1
                                stock_success = True
                                continue

                        # 재무제표 수집
                        success = self.dart_service.save_financial_to_db(
                            db, ticker, year
                        )

                        if success:
                            print(f"  {year}: ✅ Collected")
                            results['statements_collected'] += 1
                            stock_success = True
                            stock_skipped = False
                        else:
                            print(f"  {year}: ❌ Failed")

                        # DART API 속도 제한 (1초 대기)
                        time.sleep(1)

                    except Exception as e:
                        error_msg = f"{ticker} {year}: {str(e)}"
                        print(f"  {year}: ❌ Error - {e}")
                        results['errors'].append(error_msg)

                if stock_skipped:
                    results['stocks_skipped'] += 1
                elif stock_success:
                    results['stocks_success'] += 1
                else:
                    results['stocks_failed'] += 1

            except Exception as e:
                error_msg = f"Fatal error for {ticker}: {str(e)}"
                print(f"[{idx}/{len(tickers)}] ❌ {error_msg}")
                results['errors'].append(error_msg)
                results['stocks_failed'] += 1

        # 결과 요약
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        results['end_time'] = end_time.isoformat()
        results['duration_seconds'] = duration

        print(f"\n{'='*60}")
        print(f"✅ Financial Batch Collection Completed!")
        print(f"{'='*60}")
        print(f"Stocks processed: {results['stocks_processed']}")
        print(f"  - Success: {results['stocks_success']}")
        print(f"  - Failed: {results['stocks_failed']}")
        print(f"  - Skipped: {results['stocks_skipped']}")
        print(f"Statements collected: {results['statements_collected']}")
        print(f"Statements skipped: {results['statements_skipped']}")
        print(f"Duration: {duration/60:.1f} minutes")
        if results['errors']:
            print(f"Errors: {len(results['errors'])} (check details)")
        print(f"{'='*60}\n")

        return results

    def collect_all_kr_stocks(
        self,
        db: Session,
        start_year: int = 2023,
        end_year: int = 2025,
        market: Optional[str] = None,
        limit: Optional[int] = None,
        incremental: bool = False
    ) -> Dict:
        """
        한국 전체 종목 재무제표 수집

        Args:
            db: 데이터베이스 세션
            start_year: 시작 연도 (기본: 2023)
            end_year: 종료 연도 (기본: 2025)
            market: KOSPI 또는 KOSDAQ (None이면 전체)
            limit: 종목 수 제한 (테스트용)
            incremental: 증분 모드 (각 종목의 최신 연도부터만 수집)

        Returns:
            수집 결과 딕셔너리
        """
        print(f"\n{'='*60}")
        print(f"📊 Korea Stock Financial Collection")
        if incremental:
            print(f"   Mode: INCREMENTAL (collect missing years only)")
        else:
            print(f"   Mode: FULL (collect all years)")
        print(f"   Market: {market or 'ALL'}")
        print(f"   Years: {start_year}-{end_year}")
        if limit:
            print(f"   Limit: {limit} stocks (TEST MODE)")
        print(f"{'='*60}\n")

        # 종목 조회
        print("📈 Fetching stock list...")
        tickers = self.get_all_kr_stocks(db, market, limit)
        print(f"✅ Found {len(tickers)} stocks")

        if not tickers:
            return {
                'error': 'No stocks found',
                'total_stocks': 0
            }

        # 배치 수집 실행
        result = self.collect_batch(
            db,
            tickers=tickers,
            start_year=start_year,
            end_year=end_year,
            skip_existing=True,
            incremental=incremental
        )

        return result