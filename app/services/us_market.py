from datetime import datetime, timedelta
from typing import Optional
import time

import pandas as pd
import requests
from sqlalchemy.orm import Session

from app.models import Stock, StockPrice
from app.config import get_settings


class USMarketCollector:
    """미국 시장 데이터 수집기 (Finnhub + Twelve Data 조합)"""

    def __init__(self):
        settings = get_settings()
        self.finnhub_api_key = settings.finnhub_api_key
        self.twelvedata_api_key = settings.twelvedata_api_key

        self.finnhub_base_url = "https://finnhub.io/api/v1"
        self.twelvedata_base_url = "https://api.twelvedata.com"

        # S&P 500 주요 종목 샘플
        self.sp500_sample = [
            "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA",
            "META", "TSLA", "JPM", "V", "JNJ"
        ]

        if self.finnhub_api_key:
            print(f"🔑 Finnhub API Key: {self.finnhub_api_key[:8]}...")
        else:
            print("⚠️  No Finnhub API key found")

        if self.twelvedata_api_key:
            print(f"🔑 Twelve Data API Key: {self.twelvedata_api_key[:8]}...")
        else:
            print("⚠️  No Twelve Data API key found")

    def get_all_us_stocks(self, exchanges: list = None) -> pd.DataFrame:
        """
        미국 전체 주식 목록 조회 (Finnhub Stock Symbols)

        Args:
            exchanges: 거래소 리스트 (None이면 'US' = 전체)
                      예: ['US'] (권장) 또는 개별 거래소 시도

        Returns:
            주식 목록 DataFrame
        """
        if exchanges is None:
            # 기본값: 'US' = NYSE + NASDAQ + 기타 모두
            exchanges = ['US']

        all_stocks = []

        for exchange in exchanges:
            try:
                print(f"📡 Fetching stock list from {exchange}...")

                url = f"{self.finnhub_base_url}/stock/symbol"
                params = {
                    'exchange': exchange,
                    'token': self.finnhub_api_key
                }

                response = requests.get(url, params=params, timeout=30)
                response.raise_for_status()
                data = response.json()

                if not data:
                    print(f"⚠️  No stocks found for {exchange}")
                    continue

                print(f"✅ Found {len(data)} stocks from {exchange}")

                # DataFrame 변환
                df = pd.DataFrame(data)

                # 필요한 컬럼만 선택 및 정규화
                if not df.empty:
                    # Finnhub 응답 컬럼: symbol, description, displaySymbol, type, mic, figi, currency
                    df['ticker'] = df['symbol']
                    df['name'] = df['description']
                    df['market'] = df.get('mic', exchange)  # MIC (Market Identifier Code)
                    df['type'] = df.get('type', 'Common Stock')
                    df['currency'] = df.get('currency', 'USD')

                    # 필요한 컬럼만 선택
                    df = df[['ticker', 'name', 'market', 'type', 'currency']]

                    all_stocks.append(df)

                # API 속도 제한 고려
                time.sleep(1)

            except Exception as e:
                print(f"❌ Error fetching stock list from {exchange}: {e}")
                continue

        if not all_stocks:
            print("⚠️  No stocks collected from any exchange")
            return pd.DataFrame()

        # 모든 데이터 결합
        result_df = pd.concat(all_stocks, ignore_index=True)

        # 중복 제거 (ticker 기준)
        result_df = result_df.drop_duplicates(subset=['ticker'], keep='first')

        print(f"\n📊 Total unique stocks collected: {len(result_df)}")

        return result_df

    def filter_common_stocks(self, stocks_df: pd.DataFrame) -> pd.DataFrame:
        """
        일반 주식만 필터링 (ETF, Warrant 등 제외)

        Args:
            stocks_df: 주식 DataFrame

        Returns:
            필터링된 DataFrame
        """
        if stocks_df.empty:
            return stocks_df

        # 'type' 컬럼이 있으면 Common Stock만 필터링
        if 'type' in stocks_df.columns:
            before_count = len(stocks_df)
            stocks_df = stocks_df[
                stocks_df['type'].str.contains('Common Stock', case=False, na=False)
            ]
            after_count = len(stocks_df)
            print(f"🔍 Filtered: {before_count} → {after_count} (Common Stocks only)")

        return stocks_df

    def normalize_market_name(self, market: str) -> str:
        """
        거래소 이름을 표준화

        Args:
            market: 원본 거래소 이름 또는 MIC 코드

        Returns:
            표준화된 거래소 이름
        """
        # MIC 코드 매핑
        mic_map = {
            'XNYS': 'NYSE',
            'XNAS': 'NASDAQ',
            'ARCX': 'NYSE Arca',
            'BATS': 'BATS',
            'IEXG': 'IEX',
            'XASE': 'NYSE American',
            'XCHI': 'CHX',
            'XPHL': 'PHLX',
            'XBOS': 'Nasdaq BX',
            'OOTC': 'OTC',
        }

        # MIC 코드가 있으면 변환
        if market in mic_map:
            return mic_map[market]

        # 이미 표준 이름이면 그대로 사용
        if market in ['NYSE', 'NASDAQ', 'US']:
            return market

        # 문자열 매칭
        market_upper = market.upper()
        if 'NYSE' in market_upper:
            return 'NYSE'
        elif 'NASDAQ' in market_upper or 'NASD' in market_upper:
            return 'NASDAQ'

        # 알 수 없으면 앞 20자만
        return market[:20]

    def save_all_stocks_to_db(
            self,
            db: Session,
            exchanges: list = None,
            filter_common: bool = True
    ) -> dict:
        """
        미국 전체 주식 목록을 DB에 저장

        Args:
            db: 데이터베이스 세션
            exchanges: 거래소 리스트 (None이면 'US' = 전체)
            filter_common: 일반 주식만 필터링할지 여부

        Returns:
            저장 결과 딕셔너리
        """
        print(f"\n{'=' * 60}")
        print("🚀 Starting US stock list collection (Finnhub)")
        print(f"{'=' * 60}\n")

        # 전체 종목 리스트 조회
        stocks_df = self.get_all_us_stocks(exchanges)

        if stocks_df.empty:
            print("❌ No stocks to save")
            return {
                'total': 0,
                'saved': 0,
                'updated': 0,
                'failed': 0,
                'errors': []
            }

        # 일반 주식만 필터링 (옵션)
        if filter_common:
            stocks_df = self.filter_common_stocks(stocks_df)

        print(f"\n💾 Saving {len(stocks_df)} stocks to database...\n")

        results = {
            'total': len(stocks_df),
            'saved': 0,
            'updated': 0,
            'failed': 0,
            'errors': []
        }

        for idx, row in stocks_df.iterrows():
            try:
                ticker = row['ticker']
                name = row['name']
                market = self.normalize_market_name(row['market'])

                # 기존 종목 확인
                existing = db.query(Stock).filter(Stock.ticker == ticker).first()

                if existing:
                    # 업데이트
                    existing.name = name
                    existing.market = market
                    results['updated'] += 1

                    if (idx + 1) % 100 == 0:
                        print(f"  [{idx + 1}/{len(stocks_df)}] Updated: {ticker} - {name}")
                else:
                    # 신규 생성
                    stock = Stock(
                        ticker=ticker,
                        name=name,
                        market=market,
                        country='US',
                        sector=None,  # Finnhub Stock Symbols에는 sector 없음
                        industry=None
                    )
                    db.add(stock)
                    results['saved'] += 1

                    if (idx + 1) % 100 == 0:
                        print(f"  [{idx + 1}/{len(stocks_df)}] Created: {ticker} - {name}")

                # 100개마다 중간 커밋
                if (idx + 1) % 100 == 0:
                    db.commit()

            except Exception as e:
                error_msg = f"Error saving {row.get('ticker', 'unknown')}: {str(e)}"
                print(f"  ❌ {error_msg}")
                results['failed'] += 1
                results['errors'].append(error_msg)
                continue

        # 최종 커밋
        db.commit()

        print(f"\n{'=' * 60}")
        print("✅ US stock list collection completed!")
        print(f"{'=' * 60}")
        print(f"Total stocks: {results['total']}")
        print(f"  - New: {results['saved']}")
        print(f"  - Updated: {results['updated']}")
        print(f"  - Failed: {results['failed']}")
        print(f"{'=' * 60}\n")

        return results

    def get_stock_info(self, ticker: str) -> dict:
        """
        주식 기본 정보 조회 (Finnhub Company Profile)

        Args:
            ticker: 종목 코드

        Returns:
            종목 정보 딕셔너리
        """
        try:
            url = f"{self.finnhub_base_url}/stock/profile2"
            params = {
                'symbol': ticker,
                'token': self.finnhub_api_key
            }

            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            if not data or 'name' not in data:
                print(f"❌ No data found for {ticker}")
                return None

            market = self.normalize_market_name(data.get('exchange', 'NASDAQ'))

            result = {
                'ticker': ticker,
                'name': data.get('name', ticker),
                'sector': data.get('finnhubIndustry', None),
                'industry': data.get('finnhubIndustry', None),
                'market': market,
                'country': data.get('country', 'US')
            }

            print(f"✅ [Finnhub] Successfully fetched info for {ticker}: {result['name']}")
            return result

        except Exception as e:
            print(f"❌ [Finnhub] Error fetching info for {ticker}: {e}")
            return None

    def get_stock_price(
            self,
            ticker: str,
            start_date: Optional[datetime] = None,
            end_date: Optional[datetime] = None
    ) -> pd.DataFrame:
        """
        주식 가격 데이터 조회 (Twelve Data Time Series)

        Args:
            ticker: 종목 코드
            start_date: 시작일 (기본: 1년 전)
            end_date: 종료일 (기본: 오늘)

        Returns:
            가격 데이터 DataFrame
        """
        if start_date is None:
            start_date = datetime.now() - timedelta(days=365)
        if end_date is None:
            end_date = datetime.now()

        try:
            url = f"{self.twelvedata_base_url}/time_series"
            params = {
                'symbol': ticker,
                'interval': '1day',
                'outputsize': 5000,
                'apikey': self.twelvedata_api_key,
                'start_date': start_date.strftime('%Y-%m-%d'),
                'end_date': end_date.strftime('%Y-%m-%d')
            }

            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            if 'status' in data and data['status'] == 'error':
                print(f"❌ [Twelve Data] API Error for {ticker}: {data.get('message', 'Unknown error')}")
                return pd.DataFrame()

            values = data.get('values', [])
            if not values:
                print(f"❌ [Twelve Data] No price data found for {ticker}")
                return pd.DataFrame()

            df = pd.DataFrame(values)
            df['datetime'] = pd.to_datetime(df['datetime'])
            df.set_index('datetime', inplace=True)
            df = df.sort_index()

            df['Open'] = pd.to_numeric(df['open'], errors='coerce')
            df['High'] = pd.to_numeric(df['high'], errors='coerce')
            df['Low'] = pd.to_numeric(df['low'], errors='coerce')
            df['Close'] = pd.to_numeric(df['close'], errors='coerce')
            df['Volume'] = pd.to_numeric(df['volume'], errors='coerce').astype('Int64')

            df = df[['Open', 'High', 'Low', 'Close', 'Volume']]

            print(f"✅ [Twelve Data] Fetched {len(df)} price records for {ticker}")
            return df

        except Exception as e:
            print(f"❌ [Twelve Data] Error fetching price for {ticker}: {e}")
            return pd.DataFrame()

    def save_stock_to_db(self, db: Session, ticker: str) -> bool:
        """
        주식 정보를 DB에 저장

        Args:
            db: 데이터베이스 세션
            ticker: 종목 코드

        Returns:
            성공 여부
        """
        info = self.get_stock_info(ticker)

        if not info:
            return False

        try:
            existing = db.query(Stock).filter(Stock.ticker == ticker).first()

            if existing:
                existing.name = info['name']
                existing.market = info['market']
                existing.sector = info['sector']
                existing.industry = info['industry']
                print(f"📝 Updated stock: {ticker} - {info['name']}")
            else:
                stock = Stock(
                    ticker=ticker,
                    name=info['name'],
                    market=info['market'],
                    sector=info['sector'],
                    industry=info['industry'],
                    country='US'
                )
                db.add(stock)
                print(f"✨ Created new stock: {ticker} - {info['name']}")

            db.commit()
            return True

        except Exception as e:
            print(f"❌ Error saving stock {ticker}: {e}")
            db.rollback()
            return False

    def save_stock_prices_to_db(
            self,
            db: Session,
            ticker: str,
            start_date: Optional[datetime] = None
    ) -> int:
        """
        주식 가격 데이터를 DB에 저장

        Args:
            db: 데이터베이스 세션
            ticker: 종목 코드
            start_date: 시작일

        Returns:
            저장된 레코드 수
        """
        stock = db.query(Stock).filter(Stock.ticker == ticker).first()
        if not stock:
            print(f"❌ Stock {ticker} not found in database")
            return 0

        price_df = self.get_stock_price(ticker, start_date)

        if price_df.empty:
            print(f"⚠️ No price data found for {ticker}")
            return 0

        saved_count = 0

        for date_idx, row in price_df.iterrows():
            try:
                existing = db.query(StockPrice).filter(
                    StockPrice.stock_id == stock.id,
                    StockPrice.trade_date == date_idx.date()
                ).first()

                price_data = {
                    'stock_id': stock.id,
                    'trade_date': date_idx.date(),
                    'open': float(row['Open']) if pd.notna(row['Open']) else None,
                    'high': float(row['High']) if pd.notna(row['High']) else None,
                    'low': float(row['Low']) if pd.notna(row['Low']) else None,
                    'close': float(row['Close']) if pd.notna(row['Close']) else None,
                    'volume': int(row['Volume']) if pd.notna(row['Volume']) else None,
                }

                if existing:
                    for key, value in price_data.items():
                        if key not in ['stock_id', 'trade_date']:
                            setattr(existing, key, value)
                else:
                    price = StockPrice(**price_data)
                    db.add(price)

                saved_count += 1

            except Exception as e:
                print(f"❌ Error saving price for {ticker} on {date_idx}: {e}")
                continue

        db.commit()
        print(f"✅ Saved {saved_count} price records for {ticker}")
        return saved_count

    def collect_sp500_sample(self, db: Session) -> dict:
        """
        S&P 500 샘플 종목 수집

        Args:
            db: 데이터베이스 세션

        Returns:
            수집 결과 딕셔너리
        """
        results = {
            'success': 0,
            'failed': 0,
            'tickers': []
        }

        print(f"\n🚀 Starting S&P 500 sample collection ({len(self.sp500_sample)} stocks)...\n")
        print("📊 Using: Finnhub (company info) + Twelve Data (price data)\n")

        for idx, ticker in enumerate(self.sp500_sample):
            print(f"[{idx + 1}/{len(self.sp500_sample)}] Processing {ticker}...")

            if self.save_stock_to_db(db, ticker):
                results['success'] += 1
                results['tickers'].append(ticker)
            else:
                results['failed'] += 1

            if idx < len(self.sp500_sample) - 1:
                time.sleep(1)

        print(f"\n✅ Collection complete: {results['success']} succeeded, {results['failed']} failed\n")
        return results