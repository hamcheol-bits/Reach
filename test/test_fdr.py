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

print("\n" + "=" * 60)
print("테스트 완료")
print("=" * 60)