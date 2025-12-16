"""
유니크 키 수정 스크립트
unique_stock_date를 (stock_id, fiscal_date, report_type) 조합으로 변경

실행: python test/fix_unique_key.py
"""
import sys

sys.path.append('/Users/user/PycharmProjects/Reach')

from sqlalchemy import text
from app.database import SessionLocal

print("=" * 80)
print("🔧 유니크 키 수정: (stock_id, fiscal_date, report_type)")
print("=" * 80)

db = SessionLocal()

try:
    # 1. 현재 인덱스 확인
    print("\n1️⃣  현재 인덱스 확인...")
    print("-" * 80)

    result = db.execute(text("SHOW INDEX FROM financial_ratios"))
    indexes = {}
    for row in result:
        key_name = row[2]  # Key_name
        if key_name not in indexes:
            indexes[key_name] = []
        indexes[key_name].append(row[4])  # Column_name

    for key_name, columns in indexes.items():
        print(f"  {key_name}: {', '.join(columns)}")

    # 2. 기존 unique_stock_date 제거 (있다면)
    if 'unique_stock_date' in indexes:
        print("\n2️⃣  기존 unique_stock_date 제거...")
        print("-" * 80)

        db.execute(text("ALTER TABLE financial_ratios DROP INDEX unique_stock_date"))
        db.commit()
        print("✅ 기존 유니크 키 제거 완료")
    else:
        print("\n2️⃣  기존 unique_stock_date 없음")
        print("-" * 80)

    # 3. 새 유니크 키 생성
    print("\n3️⃣  새 유니크 키 생성...")
    print("-" * 80)

    try:
        db.execute(text("""
                        ALTER TABLE financial_ratios
                            ADD UNIQUE KEY unique_stock_fiscal_report (stock_id, fiscal_date, report_type)
                        """))
        db.commit()
        print("✅ 새 유니크 키 생성 완료: (stock_id, fiscal_date, report_type)")
    except Exception as e:
        if "Duplicate" in str(e):
            print("⏭️  유니크 키가 이미 존재합니다")
        else:
            raise

    # 4. 최종 인덱스 확인
    print("\n4️⃣  최종 인덱스 확인...")
    print("-" * 80)

    result = db.execute(text("SHOW INDEX FROM financial_ratios"))
    indexes = {}
    for row in result:
        key_name = row[2]
        if key_name not in indexes:
            indexes[key_name] = []
        indexes[key_name].append(row[4])

    for key_name, columns in indexes.items():
        print(f"  {key_name}: {', '.join(columns)}")

    print("\n" + "=" * 80)
    print("✅ 유니크 키 수정 완료!")
    print("=" * 80)

    print("\n💡 다음 단계:")
    print("1. 재무비율 재계산:")
    print("   curl -X POST 'http://localhost:8001/api/v1/financial/ratios/batch-calculate?limit=10'")
    print("2. 품질 확인:")
    print("   curl 'http://localhost:8001/api/v1/data-quality/summary'")

except Exception as e:
    print(f"\n❌ 오류: {e}")
    db.rollback()
    raise

finally:
    db.close()