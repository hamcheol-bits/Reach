"""
DART API 손익계산서 계정명 확인 스크립트
재무비율 계산에서 NULL 값이 나오는 원인을 파악하기 위해
실제 DART API가 반환하는 계정명을 확인합니다.
"""

import requests
from app.config import get_settings


def main():
    print("=" * 60)
    print("🔍 DART API 손익계산서 계정명 확인 (삼성전자)")
    print("=" * 60)

    settings = get_settings()

    # API 키 확인
    if not settings.dart_api_key:
        print("❌ DART_API_KEY가 설정되지 않았습니다")
        return

    print(f"🔑 DART API Key: {settings.dart_api_key[:12]}...")

    # 삼성전자 고유번호
    corp_code = "00126380"  # 삼성전자 DART 고유번호
    year = "2024"
    reprt_code = "11011"  # 연간보고서

    print(f"🔍 삼성전자 (고유번호: {corp_code})")
    print(f"📊 {year}년 연간보고서 손익계산서 조회 중...\n")

    # DART API 직접 호출
    url = "https://opendart.fss.or.kr/api/fnlttSinglAcntAll.json"
    params = {
        "crtfc_key": settings.dart_api_key,
        "corp_code": corp_code,
        "bsns_year": year,
        "reprt_code": reprt_code,
        "fs_div": "CFS"  # 연결재무제표
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()

        data = response.json()

        if data.get("status") != "000":
            print(f"❌ API 오류: {data.get('message', 'Unknown error')}")
            return

        statements = data.get("list", [])

        if not statements:
            print("❌ 재무제표 데이터를 가져올 수 없습니다")
            return

        print(f"✅ {len(statements)}개의 계정 항목을 가져왔습니다\n")

        # 손익계산서(IS) 항목만 필터링
        is_statements = [s for s in statements if s.get('sj_div') == 'IS']
        print(f"📋 손익계산서 항목: {len(is_statements)}개\n")

        # 매출, 수익, 영업이익, 당기순이익 관련 계정명 찾기
        print("=" * 60)
        print("🎯 주요 계정명 (매출, 수익, 영업이익, 당기순이익 관련)")
        print("=" * 60)

        keywords = ['매출', '수익', '영업이익', '당기순이익', '이익']

        found_accounts = []
        for stmt in is_statements:
            account_nm = stmt.get('account_nm', '')
            if any(keyword in account_nm for keyword in keywords):
                found_accounts.append({
                    'account_nm': account_nm,
                    'thstrm_amount': stmt.get('thstrm_amount', 'N/A'),
                    'account_id': stmt.get('account_id', 'N/A')
                })

        if found_accounts:
            for i, acc in enumerate(found_accounts, 1):
                print(f"{i}. 계정명: {acc['account_nm']}")
                print(f"   금액: {acc['thstrm_amount']}")
                print(f"   ID: {acc['account_id']}")
                print()
        else:
            print("❌ 주요 계정명을 찾을 수 없습니다")

        # dart_api.py에서 사용할 매핑 정보 출력
        print("\n" + "=" * 60)
        print("📝 dart_api.py 매핑에 사용할 계정명")
        print("=" * 60)

        # 매출액
        revenue_accounts = [a for a in found_accounts if '매출액' in a['account_nm']]
        if revenue_accounts:
            print(f"✅ 매출액 (revenue):")
            for acc in revenue_accounts[:3]:
                print(f"   - '{acc['account_nm']}'")

        # 영업이익
        operating_accounts = [a for a in found_accounts if '영업이익' in a['account_nm'] or '영업손익' in a['account_nm']]
        if operating_accounts:
            print(f"\n✅ 영업이익 (operating_income):")
            for acc in operating_accounts[:3]:
                print(f"   - '{acc['account_nm']}'")

        # 당기순이익
        net_income_accounts = [a for a in found_accounts if '당기순이익' in a['account_nm'] or '당기순손익' in a['account_nm']]
        if net_income_accounts:
            print(f"\n✅ 당기순이익 (net_income):")
            for acc in net_income_accounts[:3]:
                print(f"   - '{acc['account_nm']}'")

        # 모든 손익계산서 계정명 출력 (선택사항)
        print("\n" + "=" * 60)
        print("📝 전체 손익계산서 계정명 목록 (처음 50개)")
        print("=" * 60)

        for i, stmt in enumerate(is_statements[:50], 1):
            account_nm = stmt.get('account_nm', 'N/A')
            amount = stmt.get('thstrm_amount', 'N/A')
            print(f"{i:2d}. {account_nm:<40} ({amount:>15})")

        if len(is_statements) > 50:
            print(f"\n... 외 {len(is_statements) - 50}개 항목")

    except requests.exceptions.RequestException as e:
        print(f"❌ HTTP 요청 오류: {str(e)}")
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()