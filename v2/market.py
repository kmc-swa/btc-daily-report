import requests

BASE_URL = "https://fapi.binance.com"


def get_market_data(symbol="BTCUSDT"):
    # 24시간 시세
    ticker = requests.get(
        f"{BASE_URL}/fapi/v1/ticker/24hr",
        params={"symbol": symbol},
        timeout=10,
    ).json()

    # Funding Rate
    funding = requests.get(
        f"{BASE_URL}/fapi/v1/fundingRate",
        params={"symbol": symbol, "limit": 1},
        timeout=10,
    ).json()

    # Open Interest
    oi = requests.get(
        f"{BASE_URL}/fapi/v1/openInterest",
        params={"symbol": symbol},
        timeout=10,
    ).json()

    return {
        "symbol": symbol,
        "price": float(ticker["lastPrice"]),
        "change": float(ticker["priceChangePercent"]),
        "volume": float(ticker["quoteVolume"]),
        "funding": float(funding[0]["fundingRate"]),
        "open_interest": float(oi["openInterest"]),
    }
