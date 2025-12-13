"""
누락된 시가총액 수집 (2025 Q2, 2023, 2022)
실행: python test/collect_missing_market_cap.py
"""
import sys
sys.path.append('/Users/user/PycharmProjects/Reach')

from datetime import datetime, timedelta
from app.database import SessionLocal
from app.services.korea_market import KoreaMarketCollector

print("=" * 60)
print("📊 누락된 시가총액 수집")
print("=" * 60)

db = SessionLocal()
collector = KoreaMarketCollector()

# 누락된 날짜들
missing_dates = [
    "2025-06-30",  # 2025 Q2
    "2023-12-31",  # 2023년
    "2022-12-31",  # 2022년
]

print(f"\n수집할 날짜: {len(missing_dates)}개")
for date in missing_dates:
    print(f"  - {date}")

print("\n" + "=" * 60)

success_count = 0
failed_count = 0

for date_str in missing_dates:
    try:
        target_date = datetime.strptime(date_str, "%Y-%m-%d")

        print(f"\n📅 {date_str} 시가총액 수집 중...")

        # 최대 10일 전까지 거슬러 올라가며 시도 (주말/공휴일/연말 대응)
        collected = False
        for i in range(10):
            try_date = target_date - timedelta(days=i)

            # 주말 건너뛰기
            if try_date.weekday() >= 5:
                continue

            print(f"  시도 {i+1}/10: {try_date.strftime('%Y-%m-%d')} ({['월','화','수','목','금','토','일'][try_date.weekday()]}요일)")

            try:
                saved_count = collector.save_market_data_to_db(db, "KOSPI", try_date)

                if saved_count > 0:
                    print(f"  ✅ 성공: {saved_count}개 종목 시가총액 저장")
                    success_count += 1
                    collected = True
                    break
                else:
                    print(f"  ⚠️  데이터 없음 (휴장일 가능성)")
            except Exception as e:
                print(f"  ⚠️  오류: {e}")

        if not collected:
            print(f"  ❌ {date_str} 전후 10일 내 데이터 없음")
            failed_count += 1

    except Exception as e:
        print(f"  ❌ 오류: {e}")
        failed_count += 1

db.close()

print("\n" + "=" * 60)
print("✅ 수집 완료")
print("=" * 60)
print(f"성공: {success_count}/{len(missing_dates)}개 날짜")
print(f"실패: {failed_count}/{len(missing_dates)}개 날짜")
print("=" * 60)

if success_count > 0:
    print("\n💡 다음 단계:")
    print("  1. 재무비율 재계산:")
    print("     curl -X POST 'http://localhost:8001/api/v1/financial/ratios/calculate/005930'")
    print("\n  2. 결과 확인:")
    print("     curl 'http://localhost:8001/api/v1/financial/ratios/005930?limit=10'")

if failed_count > 0:
    print("\n⚠️  일부 날짜 수집 실패")
    print("  - 해당 날짜가 휴장일이거나 데이터가 없을 수 있습니다")
    print("  - pykrx API 제약일 수 있습니다")