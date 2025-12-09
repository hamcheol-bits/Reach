"""
Finnhub API 키 인증 테스트
"""
import sys

sys.path.append('/Users/user/PycharmProjects/Reach')

import requests
from app.config import get_settings

settings = get_settings()
api_key = settings.finnhub_api_key

print("=" * 60)
print("Finnhub API 키 인증 테스트")
print("=" * 60)
print(f"API Key: {api_key[:8]}..." if api_key else "❌ API Key not found!")
print()

if not api_key:
    print("⚠️ .env 파일에 FINNHUB_API_KEY를 설정해주세요")
    sys.exit(1)

# 1. 가장 간단한 엔드포인트 테스트 (Quote)
print("1. Quote API 테스트 (가장 기본)")
print("-" * 60)
url = "https://finnhub.io/api/v1/quote"
params = {
    'symbol': 'AAPL',
    'token': api_key
}

try:
    response = requests.get(url, params=params, timeout=10)
    print(f"Status: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"✅ 성공! 현재 AAPL 가격: ${data.get('c')}")
    elif response.status_code == 401:
        print("❌ 401 Unauthorized - API 키가 유효하지 않습니다")
        print(f"응답: {response.text}")
    else:
        print(f"❌ 에러 {response.status_code}")
        print(f"응답: {response.text}")
except Exception as e:
    print(f"❌ 예외 발생: {e}")

print()

# 2. Company Profile API 테스트
print("2. Company Profile API 테스트")
print("-" * 60)
url = "https://finnhub.io/api/v1/stock/profile2"
params = {
    'symbol': 'AAPL',
    'token': api_key
}

try:
    response = requests.get(url, params=params, timeout=10)
    print(f"Status: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"✅ 성공! Company: {data.get('name')}")
    elif response.status_code == 401:
        print("❌ 401 Unauthorized - API 키가 유효하지 않습니다")
    else:
        print(f"❌ 에러 {response.status_code}")
        print(f"응답: {response.text}")
except Exception as e:
    print(f"❌ 예외 발생: {e}")

print()

# 3. Stock Symbols API 테스트 (문제의 엔드포인트)
print("3. Stock Symbols API 테스트 (NYSE)")
print("-" * 60)
url = "https://finnhub.io/api/v1/stock/symbol"
params = {
    'exchange': 'US',  # NYSE 대신 US로 시도
    'token': api_key
}

try:
    response = requests.get(url, params=params, timeout=10)
    print(f"Status: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"✅ 성공! 종목 수: {len(data)}")
        if data:
            print(f"샘플: {data[0]}")
    elif response.status_code == 401:
        print("❌ 401 Unauthorized")
        print("가능한 원인:")
        print("  1. API 키가 만료됨")
        print("  2. API 키가 잘못 입력됨")
        print("  3. Stock Symbols 엔드포인트가 무료 플랜에서 제한됨")
        print(f"응답: {response.text}")
    else:
        print(f"❌ 에러 {response.status_code}")
        print(f"응답: {response.text}")
except Exception as e:
    print(f"❌ 예외 발생: {e}")

print()
print("=" * 60)
print("테스트 완료")
print("=" * 60)
print()
print("📝 다음 단계:")
print("1. 401 에러가 계속되면 https://finnhub.io/dashboard 에서 API 키 재확인")
print("2. 무료 플랜 제한이면 대안 API 사용 (yfinance 등)")
print("=" * 60)