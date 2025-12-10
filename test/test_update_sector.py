"""
pykrx 섹터 데이터 조회 디버깅 테스트
실행: python test/test_pykrx_sector.py
"""
from datetime import datetime
from pykrx import stock
import pandas as pd

print("=" * 60)
print("pykrx 섹터 데이터 조회 디버깅")
print("=" * 60)

today = datetime.now().strftime("%Y%m%d")
print(f"조회 날짜: {today}\n")

# 1. KOSPI 시가총액 데이터 조회
print("1. KOSPI 시가총액 데이터 조회")
print("-" * 60)
try:
    kospi_df = stock.get_market_cap_by_ticker(today, market="KOSPI")
    print(f"✅ KOSPI 데이터 조회 성공: {len(kospi_df)}개 종목")
    print(f"컬럼: {kospi_df.columns.tolist()}")
    print(f"\n상위 5개 데이터:")
    print(kospi_df.head())

    # Sector 컬럼 확인
    if 'Sector' in kospi_df.columns:
        print(f"\n✅ Sector 컬럼 존재!")
        sector_counts = kospi_df['Sector'].value_counts()
        print(f"\n섹터별 종목 수:")
        print(sector_counts.head(10))

        # 섹터 데이터 샘플
        print(f"\n섹터 데이터 샘플 (상위 10개):")
        for ticker, row in kospi_df.head(10).iterrows():
            name = stock.get_market_ticker_name(ticker)
            sector = row['Sector']
            print(f"{ticker:8} | {name:15} | {sector}")
    else:
        print(f"\n❌ Sector 컬럼이 없습니다!")

except Exception as e:
    print(f"❌ KOSPI 조회 실패: {e}")

print("\n" + "=" * 60)

# 2. KOSDAQ 시가총액 데이터 조회
print("2. KOSDAQ 시가총액 데이터 조회")
print("-" * 60)
try:
    kosdaq_df = stock.get_market_cap_by_ticker(today, market="KOSDAQ")
    print(f"✅ KOSDAQ 데이터 조회 성공: {len(kosdaq_df)}개 종목")
    print(f"컬럼: {kosdaq_df.columns.tolist()}")
    print(f"\n상위 5개 데이터:")
    print(kosdaq_df.head())

    # Sector 컬럼 확인
    if 'Sector' in kosdaq_df.columns:
        print(f"\n✅ Sector 컬럼 존재!")
        sector_counts = kosdaq_df['Sector'].value_counts()
        print(f"\n섹터별 종목 수:")
        print(sector_counts.head(10))

        # 섹터 데이터 샘플
        print(f"\n섹터 데이터 샘플 (상위 10개):")
        for ticker, row in kosdaq_df.head(10).iterrows():
            name = stock.get_market_ticker_name(ticker)
            sector = row['Sector']
            print(f"{ticker:8} | {name:15} | {sector}")
    else:
        print(f"\n❌ Sector 컬럼이 없습니다!")

except Exception as e:
    print(f"❌ KOSDAQ 조회 실패: {e}")

print("\n" + "=" * 60)
print("테스트 완료")
print("=" * 60)