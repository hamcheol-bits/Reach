"""
배치 데이터 수집 서비스

전체 시장의 주식 정보와 가격 데이터를 수집하는 배치 작업 관리
"""
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import time

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models import Stock, StockPrice
from app.services.korea_market import KoreaMarketCollector
from app.services.us_market import USMarketCollector


class BatchCollector:
    """배치 데이터 수집 관리자"""

    def __init__(self):
        self.korea_collector = KoreaMarketCollector()
        self.us_collector = USMarketCollector()

    def get_last_collection_date(self, db: Session, ticker: str) -> Optional[datetime]:
        """
        특정 종목의 마지막 수집 날짜 조회

        Args:
            db: 데이터베이스 세션
            ticker: 종목 코드

        Returns:
            마지막 수집 날짜 또는 None
        """
        stock = db.query(Stock).filter(Stock.ticker == ticker).first()
        if not stock:
            return None

        last_price = (
            db.query(StockPrice)
            .filter(StockPrice.stock_id == stock.id)
            .order_by(StockPrice.trade_date.desc())
            .first()
        )

        return datetime.combine(last_price.trade_date, datetime.min.time()) if last_price else None

    def collect_korea_batch(
        self,
        db: Session,
        market: str = "KOSPI",
        incremental: bool = True,
        max_stocks: Optional[int] = None
    ) -> Dict:
        """
        한국 시장 배치 수집

        Args:
            db: 데이터베이스 세션
            market: 시장 (KOSPI, KOSDAQ)
            incremental: 증분 업데이트 여부
            max_stocks: 최대 수집 종목 수 (테스트용)

        Returns:
            수집 결과 딕셔너리
        """
        print(f"\n{'='*60}")
        print(f"🚀 Starting {market} batch collection")
        print(f"   Mode: {'Incremental' if incremental else 'Full'}")
        print(f"{'='*60}\n")

        start_time = datetime.now()
        results = {
            'market': market,
            'start_time': start_time.isoformat(),
            'stocks_processed': 0,
            'stocks_success': 0,
            'stocks_failed': 0,
            'prices_saved': 0,
            'market_data_saved': 0,
            'errors': []
        }

        try:
            # 1. 주식 목록 수집 및 저장 (섹터 포함)
            print(f"📊 Step 1: Collecting stock list from {market}...")
            stocks_count = self.korea_collector.save_stocks_to_db(db, market)
            print(f"✅ Saved {stocks_count} stocks from {market}\n")

            # 2. 시장 데이터 수집 (시가총액, 거래대금, 상장주식수) ⭐ 신규
            print(f"📈 Step 2: Collecting market data (market cap, trading value, shares)...\n")
            market_data_count = self.korea_collector.save_market_data_to_db(db, market)
            results['market_data_saved'] = market_data_count
            print(f"✅ Saved {market_data_count} market data records\n")

            # 3. 각 종목의 가격 데이터 수집
            print(f"💰 Step 3: Collecting price data...\n")

            # DB에서 해당 시장의 모든 종목 조회
            stocks = (
                db.query(Stock)
                .filter(Stock.market == market, Stock.country == 'KR')
                .all()
            )

            if max_stocks:
                stocks = stocks[:max_stocks]

            print(f"Found {len(stocks)} stocks to process\n")

            for idx, stock in enumerate(stocks, 1):
                results['stocks_processed'] += 1

                try:
                    print(f"[{idx}/{len(stocks)}] Processing {stock.ticker} ({stock.name})...")

                    # 증분 업데이트: 마지막 수집일 이후부터
                    start_date = None
                    if incremental:
                        last_date = self.get_last_collection_date(db, stock.ticker)
                        if last_date:
                            start_date = last_date + timedelta(days=1)
                            print(f"   ↳ Incremental from {start_date.date()}")
                        else:
                            print(f"   ↳ First collection (1 year)")
                    else:
                        print(f"   ↳ Full collection (1 year)")

                    # 가격 데이터 수집
                    price_count = self.korea_collector.save_stock_prices_to_db(
                        db, stock.ticker, start_date
                    )

                    results['prices_saved'] += price_count
                    results['stocks_success'] += 1

                    print(f"   ✅ Saved {price_count} price records\n")

                    # API 속도 제한 고려 (0.2초 대기)
                    if idx < len(stocks):
                        time.sleep(0.2)

                except Exception as e:
                    error_msg = f"Error processing {stock.ticker}: {str(e)}"
                    print(f"   ❌ {error_msg}\n")
                    results['stocks_failed'] += 1
                    results['errors'].append(error_msg)
                    continue

        except Exception as e:
            error_msg = f"Fatal error in batch collection: {str(e)}"
            print(f"\n❌ {error_msg}\n")
            results['errors'].append(error_msg)

        # 결과 요약
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        results['end_time'] = end_time.isoformat()
        results['duration_seconds'] = duration

        print(f"\n{'='*60}")
        print(f"✅ {market} batch collection completed!")
        print(f"{'='*60}")
        print(f"Stocks processed: {results['stocks_processed']}")
        print(f"  - Success: {results['stocks_success']}")
        print(f"  - Failed: {results['stocks_failed']}")
        print(f"Market data saved: {results['market_data_saved']}")
        print(f"Price records saved: {results['prices_saved']}")
        print(f"Duration: {duration:.1f} seconds")
        print(f"{'='*60}\n")

        return results

    def collect_us_batch(
        self,
        db: Session,
        tickers: List[str] = None,
        incremental: bool = True,
        collect_all: bool = False,
        markets: Optional[List[str]] = None
    ) -> Dict:
        """
        미국 시장 배치 수집

        Args:
            db: 데이터베이스 세션
            tickers: 수집할 티커 리스트 (collect_all=False일 때 사용)
            incremental: 증분 업데이트 여부
            collect_all: True면 DB의 모든 US 종목 수집
            markets: 특정 market만 수집 (예: ['NYSE', 'NASDAQ'])

        Returns:
            수집 결과 딕셔너리
        """
        print(f"\n{'='*60}")
        print(f"🚀 Starting US market batch collection")

        # collect_all이 True면 DB에서 US 종목 조회
        if collect_all:
            query = db.query(Stock).filter(Stock.country == 'US')

            # market 필터 추가
            if markets:
                print(f"   Markets filter: {markets}")
                query = query.filter(Stock.market.in_(markets))

            us_stocks = query.all()
            tickers = [stock.ticker for stock in us_stocks]
            print(f"   Mode: Collect ALL US stocks from DB")
            print(f"   Found {len(tickers)} stocks")
        else:
            print(f"   Mode: Collect specified tickers")
            print(f"   Tickers: {len(tickers) if tickers else 0}")

        print(f"   Incremental: {'Yes' if incremental else 'No (Full)'}")
        print(f"{'='*60}\n")

        start_time = datetime.now()
        results = {
            'market': 'US',
            'markets_filter': markets,
            'collect_all': collect_all,
            'start_time': start_time.isoformat(),
            'stocks_processed': 0,
            'stocks_success': 0,
            'stocks_failed': 0,
            'prices_saved': 0,
            'errors': []
        }

        if not tickers:
            print("⚠️  No tickers to process")
            results['end_time'] = datetime.now().isoformat()
            results['duration_seconds'] = 0
            return results

        for idx, ticker in enumerate(tickers, 1):
            results['stocks_processed'] += 1

            try:
                print(f"[{idx}/{len(tickers)}] Processing {ticker}...")

                # 1. 주식 정보가 DB에 있는지 확인
                stock = db.query(Stock).filter(Stock.ticker == ticker).first()

                if not stock:
                    # DB에 없으면 정보 수집 시도
                    print(f"   ↳ Stock not in DB, fetching info...")
                    if not self.us_collector.save_stock_to_db(db, ticker):
                        raise Exception("Failed to save stock info")
                    stock = db.query(Stock).filter(Stock.ticker == ticker).first()

                # 2. 가격 데이터 수집
                start_date = None
                if incremental:
                    last_date = self.get_last_collection_date(db, ticker)
                    if last_date:
                        start_date = last_date + timedelta(days=1)
                        print(f"   ↳ Incremental from {start_date.date()}")
                    else:
                        print(f"   ↳ First collection (1 year)")
                else:
                    print(f"   ↳ Full collection (1 year)")

                price_count = self.us_collector.save_stock_prices_to_db(
                    db, ticker, start_date
                )

                results['prices_saved'] += price_count
                results['stocks_success'] += 1

                print(f"   ✅ Saved {price_count} price records\n")

                # API 속도 제한 (Twelve Data: 8/min)
                # 10초 대기 = 시간당 360개 (안전)
                if idx < len(tickers):
                    time.sleep(10)

            except Exception as e:
                error_msg = f"Error processing {ticker}: {str(e)}"
                print(f"   ❌ {error_msg}\n")
                results['stocks_failed'] += 1
                results['errors'].append(error_msg)
                continue

        # 결과 요약
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        results['end_time'] = end_time.isoformat()
        results['duration_seconds'] = duration

        print(f"\n{'='*60}")
        print(f"✅ US market batch collection completed!")
        print(f"{'='*60}")
        print(f"Stocks processed: {results['stocks_processed']}")
        print(f"  - Success: {results['stocks_success']}")
        print(f"  - Failed: {results['stocks_failed']}")
        print(f"Price records saved: {results['prices_saved']}")
        print(f"Duration: {duration/60:.1f} minutes")
        print(f"{'='*60}\n")

        return results

    def collect_all_markets(
        self,
        db: Session,
        korea_markets: List[str] = None,
        us_tickers: List[str] = None,
        us_collect_all: bool = False,
        us_markets: Optional[List[str]] = None,
        incremental: bool = True
    ) -> Dict:
        """
        모든 시장 배치 수집

        Args:
            db: 데이터베이스 세션
            korea_markets: 한국 시장 리스트 (기본: ['KOSPI', 'KOSDAQ'])
            us_tickers: 미국 티커 리스트 (us_collect_all=False일 때 사용)
            us_collect_all: True면 DB의 모든 US 종목 수집
            us_markets: 미국 시장 필터 (예: ['NYSE', 'NASDAQ'])
            incremental: 증분 업데이트 여부

        Returns:
            전체 수집 결과 딕셔너리
        """
        if korea_markets is None:
            korea_markets = ['KOSPI', 'KOSDAQ']

        if us_tickers is None and not us_collect_all:
            # 기본값: 샘플 사용 (레거시)
            us_tickers = self.us_collector.sp500_sample

        start_time = datetime.now()
        all_results = {
            'start_time': start_time.isoformat(),
            'korea': {},
            'us': {},
            'total_stocks_processed': 0,
            'total_prices_saved': 0
        }

        # 한국 시장 수집
        for market in korea_markets:
            result = self.collect_korea_batch(db, market, incremental)
            all_results['korea'][market] = result
            all_results['total_stocks_processed'] += result['stocks_processed']
            all_results['total_prices_saved'] += result['prices_saved']

        # 미국 시장 수집
        us_result = self.collect_us_batch(
            db,
            tickers=us_tickers,
            incremental=incremental,
            collect_all=us_collect_all,
            markets=us_markets
        )
        all_results['us'] = us_result
        all_results['total_stocks_processed'] += us_result['stocks_processed']
        all_results['total_prices_saved'] += us_result['prices_saved']

        # 전체 요약
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        all_results['end_time'] = end_time.isoformat()
        all_results['duration_seconds'] = duration

        print(f"\n{'='*60}")
        print(f"🎉 ALL MARKETS BATCH COLLECTION COMPLETED!")
        print(f"{'='*60}")
        print(f"Total stocks processed: {all_results['total_stocks_processed']}")
        print(f"Total price records: {all_results['total_prices_saved']}")
        print(f"Total duration: {duration/60:.1f} minutes")
        print(f"{'='*60}\n")

        return all_results