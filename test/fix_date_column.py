"""
DB 마이그레이션 스크립트 (완전판)
financial_ratios 테이블의 date 컬럼 제거 및 fiscal_date 사용

실행: python test/fix_date_column.py
"""
import sys

sys.path.append('/Users/user/PycharmProjects/Reach')

from sqlalchemy import text
from app.database import SessionLocal

print("=" * 80)
print("🔧 DB 마이그레이션: date 컬럼 제거 및 fiscal_date 사용")
print("=" * 80)

db = SessionLocal()

try:
    # 1. 현재 테이블 구조 확인
    print("\n1️⃣  현재 테이블 구조 확인...")
    print("-" * 80)

    result = db.execute(text("DESCRIBE financial_ratios"))
    columns = [row[0] for row in result]

    print(f"현재 컬럼: {', '.join(columns)}")

    has_date = 'date' in columns
    has_fiscal_date = 'fiscal_date' in columns

    print(f"  - date 컬럼: {'있음' if has_date else '없음'}")
    print(f"  - fiscal_date 컬럼: {'있음' if has_fiscal_date else '없음'}")

    # 2. fiscal_date가 없으면 추가
    if not has_fiscal_date:
        print("\n2️⃣  fiscal_date 컬럼 추가...")
        print("-" * 80)

        db.execute(text("""
                        ALTER TABLE financial_ratios
                            ADD COLUMN fiscal_date DATE AFTER stock_id
                        """))

        # date → fiscal_date 데이터 복사
        if has_date:
            db.execute(text("""
                            UPDATE financial_ratios
                            SET fiscal_date = date
                            WHERE fiscal_date IS NULL
                            """))
            print("✅ date → fiscal_date 데이터 복사 완료")

        db.commit()
        print("✅ fiscal_date 컬럼 추가 완료")
    else:
        print("\n2️⃣  fiscal_date 컬럼 이미 존재")
        print("-" * 80)

    # 3. report_type이 없으면 추가
    if 'report_type' not in columns:
        print("\n3️⃣  report_type 컬럼 추가...")
        print("-" * 80)

        db.execute(text("""
                        ALTER TABLE financial_ratios
                            ADD COLUMN report_type VARCHAR(20) AFTER fiscal_date
                        """))

        # 기본값 설정
        db.execute(text("""
                        UPDATE financial_ratios
                        SET report_type = 'annual'
                        WHERE report_type IS NULL
                        """))

        db.commit()
        print("✅ report_type 컬럼 추가 완료")
    else:
        print("\n3️⃣  report_type 컬럼 이미 존재")
        print("-" * 80)

    # 4. date 컬럼이 있으면 제거
    if has_date:
        print("\n4️⃣  date 컬럼 제거...")
        print("-" * 80)

        # 인덱스 먼저 제거 (있을 경우)
        try:
            db.execute(text("DROP INDEX idx_financial_ratios_date ON financial_ratios"))
            print("  ✅ date 컬럼 인덱스 제거")
        except Exception as e:
            if "check that it exists" in str(e).lower():
                print("  ⏭️  date 인덱스 없음 (정상)")
            else:
                print(f"  ⚠️  인덱스 제거 실패: {e}")

        # 컬럼 제거
        db.execute(text("ALTER TABLE financial_ratios DROP COLUMN date"))
        db.commit()
        print("✅ date 컬럼 제거 완료")
    else:
        print("\n4️⃣  date 컬럼 이미 제거됨")
        print("-" * 80)

    # 5. 인덱스 추가
    print("\n5️⃣  인덱스 추가...")
    print("-" * 80)

    try:
        db.execute(text("""
                        CREATE INDEX idx_financial_ratios_fiscal_date
                            ON financial_ratios (fiscal_date)
                        """))
        print("✅ fiscal_date 인덱스 생성")
    except Exception as e:
        if "Duplicate" in str(e) or "already exists" in str(e):
            print("⏭️  fiscal_date 인덱스 이미 존재")
        else:
            print(f"⚠️  인덱스 생성 실패: {e}")

    try:
        db.execute(text("""
                        CREATE INDEX idx_financial_ratios_report_type
                            ON financial_ratios (report_type)
                        """))
        print("✅ report_type 인덱스 생성")
    except Exception as e:
        if "Duplicate" in str(e) or "already exists" in str(e):
            print("⏭️  report_type 인덱스 이미 존재")
        else:
            print(f"⚠️  인덱스 생성 실패: {e}")

    db.commit()

    # 6. 최종 확인
    print("\n6️⃣  최종 테이블 구조 확인...")
    print("-" * 80)

    result = db.execute(text("DESCRIBE financial_ratios"))
    for row in result:
        print(f"  {row[0]:20s} {row[1]:20s} {row[2]:10s}")

    print("\n" + "=" * 80)
    print("✅ 마이그레이션 완료!")
    print("=" * 80)

    print("\n💡 다음 단계:")
    print("1. 서버 재시작 (이미 실행 중이면 그대로)")
    print("2. 재무비율 재계산:")
    print("   curl -X POST 'http://localhost:8001/api/v1/financial/ratios/batch-calculate?limit=10'")
    print("3. 품질 리포트 확인:")
    print("   curl 'http://localhost:8001/api/v1/data-quality/summary'")

except Exception as e:
    print(f"\n❌ 마이그레이션 실패: {e}")
    db.rollback()
    raise

finally:
    db.close()