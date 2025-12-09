"""
FinanceDataReader 테스트 스크립트
실행: python test_fdr.py
"""
import FinanceDataReader as fdr
import pandas as pd

print("=" * 60)
print("FinanceDataReader 테스트")
print("=" * 60)

# 1. KOSPI 테스트
print("\n1. KOSPI 종목 리스트 테스트")
print("-" * 60)
try:
    kospi = fdr.StockListing('KOSPI')
    print(f"✅ KOSPI 성공: {len(kospi)}개 종목")
    print(f"컬럼: {kospi.columns.tolist()}")
    print("\n샘플 데이터 (상위 5개):")
    print(kospi.head())
except Exception as e:
    print(f"❌ KOSPI 실패: {e}")

# 2. KOSDAQ 테스트
print("\n2. KOSDAQ 종목 리스트 테스트")
print("-" * 60)
try:
    kosdaq = fdr.StockListing('KOSDAQ')
    print(f"✅ KOSDAQ 성공: {len(kosdaq)}개 종목")
    print(f"컬럼: {kosdaq.columns.tolist()}")
    print("\n샘플 데이터 (상위 5개):")
    print(kosdaq.head())
except Exception as e:
    print(f"❌ KOSDAQ 실패: {e}")

# 3. KRX (전체) 테스트
print("\n3. KRX (전체 시장) 종목 리스트 테스트")
print("-" * 60)
try:
    krx = fdr.StockListing('KRX')
    print(f"✅ KRX 성공: {len(krx)}개 종목")
    print(f"컬럼: {krx.columns.tolist()}")
    print("\n샘플 데이터 (상위 5개):")
    print(krx.head())
except Exception as e:
    print(f"❌ KRX 실패: {e}")

# 4. 삼성전자 주가 테스트
print("\n4. 삼성전자(005930) 주가 데이터 테스트")
print("-" * 60)
try:
    samsung = fdr.DataReader('005930', '2024-01-01', '2024-12-31')
    print(f"✅ 삼성전자 주가 성공: {len(samsung)}개 레코드")
    print(f"컬럼: {samsung.columns.tolist()}")
    print("\n최근 5일 데이터:")
    print(samsung.tail())
except Exception as e:
    print(f"❌ 삼성전자 주가 실패: {e}")

# 5. S&P 500 종목 리스트 테스트
print("\n5. S&P 500 종목 리스트 테스트")
print("-" * 60)
try:
    sp500 = fdr.StockListing('S&P500')
    print(f"✅ S&P 500 성공: {len(sp500)}개 종목")
    print(f"컬럼: {sp500.columns.tolist()}")
    print("\n샘플 데이터 (상위 10개):")
    print(sp500.head(10))
except Exception as e:
    print(f"❌ S&P 500 실패: {e}")

# 6. Apple(AAPL) 주가 테스트
print("\n6. Apple(AAPL) 주가 데이터 테스트")
print("-" * 60)
try:
    aapl = fdr.DataReader('AAPL', '2024-01-01', '2024-12-31')
    print(f"✅ Apple 주가 성공: {len(aapl)}개 레코드")
    print(f"컬럼: {aapl.columns.tolist()}")
    print("\n최근 5일 데이터:")
    print(aapl.tail())
except Exception as e:
    print(f"❌ Apple 주가 실패: {e}")

# 7. NASDAQ 100 종목 리스트 테스트
print("\n7. NASDAQ 100 종목 리스트 테스트")
print("-" * 60)
try:
    nasdaq100 = fdr.StockListing('NASDAQ100')
    print(f"✅ NASDAQ 100 성공: {len(nasdaq100)}개 종목")
    print(f"컬럼: {nasdaq100.columns.tolist()}")
    print("\n샘플 데이터 (상위 10개):")
    print(nasdaq100.head(10))
except Exception as e:
    print(f"❌ NASDAQ 100 실패: {e}")

# 8. Microsoft(MSFT) 주가 테스트
print("\n8. Microsoft(MSFT) 주가 데이터 테스트")
print("-" * 60)
try:
    msft = fdr.DataReader('MSFT', '2024-01-01', '2024-12-31')
    print(f"✅ Microsoft 주가 성공: {len(msft)}개 레코드")
    print(f"컬럼: {msft.columns.tolist()}")
    print("\n최근 5일 데이터:")
    print(msft.tail())
except Exception as e:
    print(f"❌ Microsoft 주가 실패: {e}")

print("\n" + "=" * 60)
print("테스트 완료")
print("=" * 60)