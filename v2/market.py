import requests

BASE_URL = "https://fapi.binance.com"
OI_HIST_URL = f"{BASE_URL}/futures/data/openInterestHist"


def get_open_interest_change(symbol="BTCUSDT", period="1h", limit=24):
    """최근 `limit`개 구간(기본 24시간, 1시간 단위)의 미결제약정 히스토리를 가져와
    구간 시작 대비 변화율(%)을 계산한다. 조회 실패 시 0.0을 반환한다."""
    try:
        resp = requests.get(
            OI_HIST_URL,
            params={"symbol": symbol, "period": period, "limit": limit},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        if len(data) < 2:
            return 0.0

        oldest = float(data[0]["sumOpenInterest"])
        newest = float(data[-1]["sumOpenInterest"])
        if oldest == 0:
            return 0.0
        return (newest - oldest) / oldest * 100
    except Exception as e:
        print(f"[미결제약정 히스토리 조회 실패, 0으로 처리] {e}")
        return 0.0


def _get_json(url, params):
    """Binance 응답을 가져오되, 예상한 필드가 없는 경우(지역 차단/에러 응답 등)
    원본 응답 내용을 그대로 노출하는 예외를 던진다. (KeyError로 뭉개지 않기 위함)"""
    resp = requests.get(url, params=params, timeout=10)
    data = resp.json()
    if isinstance(data, dict) and ("code" in data and "msg" in data):
        raise RuntimeError(
            f"Binance API 에러 응답 (status={resp.status_code}): {data}"
        )
    return data


def get_market_data(symbol="BTCUSDT"):
    # 24시간 시세
    ticker = _get_json(f"{BASE_URL}/fapi/v1/ticker/24hr", {"symbol": symbol})

    # Funding Rate
    funding = _get_json(f"{BASE_URL}/fapi/v1/fundingRate", {"symbol": symbol, "limit": 1})

    # Open Interest
    oi = _get_json(f"{BASE_URL}/fapi/v1/openInterest", {"symbol": symbol})

    return {
        "symbol": symbol,
        "price": float(ticker["lastPrice"]),
        "change": float(ticker["priceChangePercent"]),
        "volume": float(ticker["quoteVolume"]),
        "funding": float(funding[0]["fundingRate"]),
        "open_interest": float(oi["openInterest"]),
        "oi_change_24h": get_open_interest_change(symbol),
    }
