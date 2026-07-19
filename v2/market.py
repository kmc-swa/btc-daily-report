import requests

# Binance Futures API는 GitHub Actions(미국 클라우드 IP)에서 HTTP 451로 차단되어
# Bybit v5 API로 대체함. (자세한 내용은 커밋 로그 참고)
BASE_URL = "https://api.bybit.com"


def _get_json(url, params):
    """Bybit 응답을 가져오되, retCode != 0(에러)이면 원본 메시지를 그대로 노출하는
    예외를 던진다."""
    resp = requests.get(url, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    if data.get("retCode") != 0:
        raise RuntimeError(f"Bybit API 에러 응답: {data}")
    return data["result"]


def get_open_interest_change(symbol="BTCUSDT", interval="1h", limit=24):
    """최근 `limit`개 구간(기본 24시간, 1시간 단위)의 미결제약정 히스토리를 가져와
    구간 시작 대비 변화율(%)을 계산한다. 조회 실패 시 0.0을 반환한다."""
    try:
        result = _get_json(
            f"{BASE_URL}/v5/market/open-interest",
            {
                "category": "linear",
                "symbol": symbol,
                "intervalTime": interval,
                "limit": limit,
            },
        )
        items = result.get("list", [])
        if len(items) < 2:
            return 0.0

        # timestamp 오름차순 정렬(오래된 것 -> 최신 것)
        items = sorted(items, key=lambda x: int(x["timestamp"]))
        oldest = float(items[0]["openInterest"])
        newest = float(items[-1]["openInterest"])
        if oldest == 0:
            return 0.0
        return (newest - oldest) / oldest * 100
    except Exception as e:
        print(f"[미결제약정 히스토리 조회 실패, 0으로 처리] {e}")
        return 0.0


def get_market_data(symbol="BTCUSDT"):
    result = _get_json(
        f"{BASE_URL}/v5/market/tickers",
        {"category": "linear", "symbol": symbol},
    )
    ticker = result["list"][0]

    return {
        "symbol": symbol,
        "price": float(ticker["lastPrice"]),
        "change": float(ticker["price24hPcnt"]) * 100,
        "volume": float(ticker["turnover24h"]),
        "funding": float(ticker["fundingRate"]),
        "open_interest": float(ticker["openInterest"]),
        "oi_change_24h": get_open_interest_change(symbol),
    }
