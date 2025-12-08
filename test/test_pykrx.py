"""
pykrx 테스트 스크립트
실행: python test_pykrx.py
"""
from pykrx import stock
from datetime import datetime, timedelta

print("=" * 60)
print("pykrx 테스트")
print("=" * 60)

today = datetime.now().strftime("%Y%m%d")
yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")

# 1. KOSPI 종목 리스트
print("\n1. KOSPI 종목 리스트 테스트")
print("-" * 60)
try:
    kospi_tickers = stock.get_market_ticker_list(today, market="KOSPI")
    print(f"✅ KOSPI 성공: {len(kospi_tickers)}개 종목")
    print(f"샘플 (상위 10개): {kospi_tickers[:10]}")

    # 삼성전자 종목명 조회
    samsung_name = stock.get_market_ticker_name("005930")
    print(f"삼성전자(005930): {samsung_name}")
except Exception as e:
    print(f"❌ KOSPI 실패: {e}")

# 2. KOSDAQ 종목 리스트
print("\n2. KOSDAQ 종목 리스트 테스트")
print("-" * 60)
try:
    kosdaq_tickers = stock.get_market_ticker_list(today, market="KOSDAQ")
    print(f"✅ KOSDAQ 성공: {len(kosdaq_tickers)}개 종목")
    print(f"샘플 (상위 10개): {kosdaq_tickers[:10]}")
except Exception as e:
    print(f"❌ KOSDAQ 실패: {e}")

# 3. 삼성전자 OHLCV 데이터
print("\n3. 삼성전자 OHLCV 데이터 테스트")
print("-" * 60)
try:
    start = "20240101"
    end = today
    df = stock.get_market_ohlcv_by_date(start, end, "005930")
    print(f"✅ 삼성전자 OHLCV 성공: {len(df)}개 레코드")
    print(f"컬럼: {df.columns.tolist()}")
    print("\n최근 5일:")
    print(df.tail())
except Exception as e:
    print(f"❌ 삼성전자 OHLCV 실패: {e}")

print("\n" + "=" * 60)
print("테스트 완료")
print("=" * 60)