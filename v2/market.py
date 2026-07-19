import requests

# Binance Futures API(HTTP 451)와 Bybit API(HTTP 403) 모두 GitHub Actions의
# 클라우드 IP를 차단해서, 대신 CoinGecko의 무료 공개 파생상품 API로 대체함.
# CoinGecko가 여러 거래소 데이터를 서버 사이드에서 수집해 제공하는 방식이라
# 클라우드 IP 차단 문제가 없다. (자세한 내용은 커밋 로그 참고)
DERIVATIVES_URL = "https://api.coingecko.com/api/v3/derivatives"


def get_market_data(symbol="BTCUSDT", market="Binance (Futures)"):
    """CoinGecko 파생상품 티커 목록에서 지정한 심볼/거래소의 데이터를 찾아 반환한다.
    지정한 거래소 데이터가 없으면 동일 심볼의 다른 거래소 데이터로 폴백한다.

    참고: CoinGecko는 미결제약정의 과거 이력(24h 변화율)을 무료로 제공하지 않아서
    oi_change_24h는 이번 버전에서는 계산하지 않는다(0.0으로 처리, 추후 자체 저장 방식으로 추가 예정).
    """
    resp = requests.get(DERIVATIVES_URL, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    ticker = next(
        (t for t in data if t.get("symbol") == symbol and t.get("market") == market),
        None,
    )
    if ticker is None:
        ticker = next((t for t in data if t.get("symbol") == symbol), None)
    if ticker is None:
        raise RuntimeError(f"CoinGecko derivatives에서 {symbol} 데이터를 찾지 못했습니다.")

    # CoinGecko의 funding_rate는 퍼센트 단위로 추정됨(예: 0.0056 = 0.0056%).
    # 기존 스코어 로직은 소수 비율 기준(0.0001 = 0.01%)이라 100으로 나눠 맞춘다.
    funding_pct = float(ticker.get("funding_rate") or 0.0)

    return {
        "symbol": symbol,
        "price": float(ticker["price"]),
        "change": float(ticker.get("price_percentage_change_24h") or 0.0),
        "volume": float(ticker.get("volume_24h") or 0.0),
        "funding": funding_pct / 100,
        "open_interest": float(ticker.get("open_interest") or 0.0),
        "oi_change_24h": 0.0,  # CoinGecko는 과거 미결제약정 데이터 미제공
    }
