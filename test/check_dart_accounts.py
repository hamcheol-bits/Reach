"""
DART API 손익계산서 계정명 확인
실행: python test/check_dart_accounts.py
"""
import sys

sys.path.append('/Users/user/PycharmProjects/Reach')

from app.services.dart_api import DartApiService

print("=" * 60)
print("🔍 DART API 손익계산서 계정명 확인 (삼성전자)")
print("=" * 60)

dart = DartApiService()

# 삼성전자 2024년 재무제표 조회
corp_code = dart.get_corp_code("005930")

if not corp_code:
    print("❌ 고유번호를 찾을 수 없습니다")
    sys.exit(1)

# 2024년 연간 재무제표
df = dart.get_financial_statement(corp_code, 2024, report_code="11011")

if df is None or df.empty:
    print("❌ 재무제표 조회 실패")
    sys.exit(1)

print(f"\n✅ 재무제표 조회 성공: {len(df)}개 항목\n")

# 손익계산서만 필터링
is_df = df[df['sj_div'] == 'IS']

print("=" * 80)
print("손익계산서 (IS) - 모든 계정명")
print("=" * 80)

print(f"\n{'계정명':<50} {'당기금액':>20}")
print("-" * 80)

for _, row in is_df.iterrows():
    account_nm = row.get('account_nm', '')
    thstrm_amount = row.get('thstrm_amount', '0')

    print(f"{account_nm:<50} {thstrm_amount:>20}")

print("\n" + "=" * 80)

# 우리가 찾는 주요 계정명
target_keywords = ['매출', '수익', '영업이익', '당기순이익', '이익']

print("\n주요 키워드 포함 계정명:")
print("=" * 80)

for keyword in target_keywords:
    print(f"\n🔍 '{keyword}' 포함:")
    found = False
    for _, row in is_df.iterrows():
        account_nm = row.get('account_nm', '')
        if keyword in account_nm:
            thstrm_amount = row.get('thstrm_amount', '0')
            print(f"  - {account_nm:<45} : {thstrm_amount:>20}")
            found = True

    if not found:
        print(f"  ❌ '{keyword}' 포함 계정명 없음")

print("\n" + "=" * 80)