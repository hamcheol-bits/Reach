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
        # config.py의 Settings에서 API 키 가져오기
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

    def _normalize_market(self, exchange: str) -> str:
        """
        거래소 이름을 간단하게 정규화

        Args:
            exchange: 원본 거래소 이름

        Returns:
            정규화된 거래소 이름 (최대 10자)
        """
        # 매핑 테이블
        exchange_map = {
            'NASDAQ NMS - GLOBAL MARKET': 'NASDAQ',
            'NEW YORK STOCK EXCHANGE, INC.': 'NYSE',
            'NYSE': 'NYSE',
            'NASDAQ': 'NASDAQ',
        }

        # 매핑에 있으면 사용, 없으면 앞 10자만
        normalized = exchange_map.get(exchange.upper(), exchange[10])
        return normalized

    def get_stock_info(self, ticker: str) -> dict:
        """
        주식 기본 정보 조회 (Finnhub Company Profile - 무료)

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

            # 빈 응답 체크
            if not data or 'name' not in data:
                print(f"❌ No data found for {ticker}")
                return None

            # market 값 정규화 (최대 50자)
            raw_market = data.get('exchange', 'NASDAQ')
            market = self._normalize_market(raw_market)

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
        주식 가격 데이터 조회 (Twelve Data Time Series - 무료)

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

            # 에러 체크
            if 'status' in data and data['status'] == 'error':
                print(f"❌ [Twelve Data] API Error for {ticker}: {data.get('message', 'Unknown error')}")
                return pd.DataFrame()

            # 데이터 추출
            values = data.get('values', [])
            if not values:
                print(f"❌ [Twelve Data] No price data found for {ticker}")
                return pd.DataFrame()

            # DataFrame 생성
            df = pd.DataFrame(values)
            df['datetime'] = pd.to_datetime(df['datetime'])
            df.set_index('datetime', inplace=True)
            df = df.sort_index()

            # 컬럼명 정규화 및 타입 변환
            df['Open'] = pd.to_numeric(df['open'], errors='coerce')
            df['High'] = pd.to_numeric(df['high'], errors='coerce')
            df['Low'] = pd.to_numeric(df['low'], errors='coerce')
            df['Close'] = pd.to_numeric(df['close'], errors='coerce')
            df['Volume'] = pd.to_numeric(df['volume'], errors='coerce').astype('Int64')

            # 필요한 컬럼만 선택
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
            # 기존 종목 확인
            existing = db.query(Stock).filter(Stock.ticker == ticker).first()

            if existing:
                # 업데이트
                existing.name = info['name']
                existing.market = info['market']
                existing.sector = info['sector']
                existing.industry = info['industry']
                print(f"📝 Updated stock: {ticker} - {info['name']}")
            else:
                # 신규 생성
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
        # 주식 정보 조회
        stock = db.query(Stock).filter(Stock.ticker == ticker).first()
        if not stock:
            print(f"❌ Stock {ticker} not found in database")
            return 0

        # 가격 데이터 조회
        price_df = self.get_stock_price(ticker, start_date)

        if price_df.empty:
            print(f"⚠️ No price data found for {ticker}")
            return 0

        saved_count = 0

        for date_idx, row in price_df.iterrows():
            try:
                # 기존 데이터 확인
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
                    # 업데이트
                    for key, value in price_data.items():
                        if key not in ['stock_id', 'trade_date']:
                            setattr(existing, key, value)
                else:
                    # 신규 생성
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

            # Finnhub: 분당 60회 (충분히 빠름)
            # 안전하게 1초 대기
            if idx < len(self.sp500_sample) - 1:
                time.sleep(1)

        print(f"\n✅ Collection complete: {results['success']} succeeded, {results['failed']} failed\n")
        return results
