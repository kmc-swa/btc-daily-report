"""
매일 아침 비트코인 시세 + 국내외 뉴스 요약을 텔레그램으로 전송하는 스크립트.

필요한 환경변수 (GitHub Actions Secrets에 등록):
  TELEGRAM_BOT_TOKEN : @BotFather에서 발급받은 봇 토큰
  TELEGRAM_CHAT_ID   : 메시지를 받을 chat_id

데이터 소스:
  - 시세/지지·저항선: Upbit 공개 API (KRW-BTC, 일봉 캔들)
  - 국내 뉴스: 네이버 뉴스 검색 RSS ("비트코인")
  - 해외 뉴스: CoinDesk RSS
"""

import os
import sys
import statistics
import requests
import feedparser
from datetime import datetime, timezone, timedelta

KST = timezone(timedelta(hours=9))

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

UPBIT_CANDLES_URL = "https://api.upbit.com/v1/candles/days"
UPBIT_TICKER_URL = "https://api.upbit.com/v1/ticker"

NAVER_NEWS_RSS = "https://search.naver.com/search.naver?where=rss&query=비트코인"
COINDESK_RSS = "https://www.coindesk.com/arc/outboundfeeds/rss/"


def get_price_and_levels():
    """현재가, 24시간 변동률, 최근 20일 기준 지지/저항선을 계산."""
    ticker_resp = requests.get(UPBIT_TICKER_URL, params={"markets": "KRW-BTC"}, timeout=10)
    ticker_resp.raise_for_status()
    ticker = ticker_resp.json()[0]

    current_price = ticker["trade_price"]
    change_rate = ticker["signed_change_rate"] * 100  # %
    change_price = ticker["signed_change_price"]

    candle_resp = requests.get(
        UPBIT_CANDLES_URL, params={"market": "KRW-BTC", "count": 20}, timeout=10
    )
    candle_resp.raise_for_status()
    candles = candle_resp.json()

    highs = [c["high_price"] for c in candles]
    lows = [c["low_price"] for c in candles]

    # 단순화된 지지/저항선: 최근 20일 고가/저가의 평균과 극값
    resistance_strong = max(highs)
    resistance_avg = statistics.mean(sorted(highs, reverse=True)[:5])
    support_avg = statistics.mean(sorted(lows)[:5])
    support_strong = min(lows)

    return {
        "current_price": current_price,
        "change_rate": change_rate,
        "change_price": change_price,
        "resistance_strong": resistance_strong,
        "resistance_avg": resistance_avg,
        "support_avg": support_avg,
        "support_strong": support_strong,
    }


def get_domestic_news(limit=3):
    feed = feedparser.parse(NAVER_NEWS_RSS)
    items = []
    for entry in feed.entries[:limit]:
        title = entry.get("title", "").strip()
        link = entry.get("link", "")
        items.append((title, link))
    return items


def get_global_news(limit=3):
    feed = feedparser.parse(COINDESK_RSS)
    items = []
    for entry in feed.entries:
        title = entry.get("title", "")
        if "bitcoin" in title.lower() or "btc" in title.lower():
            items.append((title.strip(), entry.get("link", "")))
        if len(items) >= limit:
            break
    # 비트코인 관련 기사가 부족하면 일반 기사로 채움
    if len(items) < limit:
        for entry in feed.entries[:limit]:
            pair = (entry.get("title", "").strip(), entry.get("link", ""))
            if pair not in items:
                items.append(pair)
            if len(items) >= limit:
                break
    return items[:limit]


def format_message(price_data, domestic_news, global_news):
    now = datetime.now(KST).strftime("%Y-%m-%d (%a) %H:%M")
    p = price_data

    arrow = "🔺" if p["change_rate"] >= 0 else "🔻"

    lines = []
    lines.append(f"📊 *비트코인 데일리 브리핑* — {now} KST")
    lines.append("")
    lines.append(f"💰 현재가: *{p['current_price']:,.0f}원*")
    lines.append(f"{arrow} 변동: {p['change_rate']:+.2f}% ({p['change_price']:+,.0f}원, 24h)")
    lines.append("")
    lines.append("📐 지지/저항선 (최근 20일 기준)")
    lines.append(f"  저항(강): {p['resistance_strong']:,.0f}원")
    lines.append(f"  저항(평균): {p['resistance_avg']:,.0f}원")
    lines.append(f"  지지(평균): {p['support_avg']:,.0f}원")
    lines.append(f"  지지(강): {p['support_strong']:,.0f}원")
    lines.append("")
    lines.append("🇰🇷 국내 뉴스")
    for title, link in domestic_news:
        lines.append(f"  • [{title}]({link})")
    lines.append("")
    lines.append("🌍 해외 뉴스")
    for title, link in global_news:
        lines.append(f"  • [{title}]({link})")

    return "\n".join(lines)


def send_telegram_message(text):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("ERROR: TELEGRAM_BOT_TOKEN 또는 TELEGRAM_CHAT_ID 환경변수가 설정되지 않았습니다.")
        sys.exit(1)

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    resp = requests.post(
        url,
        data={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": text,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True,
        },
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()


def main():
    price_data = get_price_and_levels()
    domestic_news = get_domestic_news()
    global_news = get_global_news()
    message = format_message(price_data, domestic_news, global_news)
    print(message)  # 로그 확인용
    send_telegram_message(message)
    print("\n[전송 완료]")


if __name__ == "__main__":
    main()
