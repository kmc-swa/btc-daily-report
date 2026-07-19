"""
v2 메인 스크립트 (Sprint 1-1: Binance Futures 데이터 엔진 + AI 해석)

market.py에서 가져온 Binance Futures 데이터(시세/펀딩비/미결제약정)를 바탕으로
규칙 기반 시장 판단을 만들고, ANTHROPIC_API_KEY가 설정돼 있으면 Claude API로
자연어 해석 문단까지 생성한다. 아직 텔레그램 발송은 하지 않고 콘솔에 출력만 한다
(v1이 계속 매일 7시 발송을 담당하고, v2는 완성되면 이어받을 예정).

환경변수:
    ANTHROPIC_API_KEY (선택) - 없으면 규칙 기반 해석 문장으로 자동 대체됨.
"""

import os

from market import get_market_data


def rule_based_mood(data):
    """펀딩비/변동률 기반 규칙 해석 (AI 미사용 시 폴백)."""
    funding = data["funding"]
    change = data["change"]

    if change > 2 and funding > 0.0005:
        mood = "상승 과열"
        note = "가격 상승과 함께 롱 포지션이 몰려 있어 단기 조정 가능성에 유의하세요."
    elif change < -2 and funding < -0.0005:
        mood = "하락 과열"
        note = "가격 하락과 함께 숏 포지션이 몰려 있어 숏스퀴즈(반등) 가능성에 유의하세요."
    elif funding > 0.0003:
        mood = "롱 우세"
        note = "펀딩비가 플러스로, 롱 포지션이 다소 우세한 상태입니다."
    elif funding < -0.0003:
        mood = "숏 우세"
        note = "펀딩비가 마이너스로, 숏 포지션이 다소 우세한 상태입니다."
    else:
        mood = "중립"
        note = "펀딩비가 중립 범위로, 특별한 쏠림은 관찰되지 않습니다."

    return mood, note


def ai_interpretation(data, mood, note):
    """ANTHROPIC_API_KEY가 있으면 Claude로 자연어 해석을 생성하고,
    없거나 호출에 실패하면 규칙 기반 문장(note)을 그대로 반환한다."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return note

    try:
        import anthropic

        client = anthropic.Anthropic(api_key=api_key)
        prompt = (
            "다음은 비트코인 무기한 선물(Binance) 데이터입니다.\n"
            f"- 현재가: {data['price']:,.0f} USDT\n"
            f"- 24시간 변동률: {data['change']:+.2f}%\n"
            f"- 24시간 거래대금: {data['volume']:,.0f} USDT\n"
            f"- 펀딩비: {data['funding']:.5f}\n"
            f"- 미결제약정: {data['open_interest']:,.0f} BTC\n"
            f"- 규칙 기반 판단: {mood}\n\n"
            "위 데이터를 바탕으로 2~3문장으로 오늘의 시장 분위기와 주의할 점을 "
            "한국어로 간결하게 설명해줘. 투자 조언이 아니라 참고용 해설 톤을 유지해."
        )
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text.strip()
    except Exception as e:  # API 실패 시 규칙 기반으로 조용히 폴백
        print(f"[AI 해석 실패, 규칙 기반으로 대체] {e}")
        return note


def build_report(symbol="BTCUSDT"):
    data = get_market_data(symbol)
    mood, note = rule_based_mood(data)
    interpretation = ai_interpretation(data, mood, note)

    lines = [
        f"📈 {symbol} Futures 리포트 (v2)",
        "",
        f"현재가: {data['price']:,.0f} USDT",
        f"24h 변동: {data['change']:+.2f}%",
        f"24h 거래대금: {data['volume']:,.0f} USDT",
        f"펀딩비: {data['funding']:.5f}",
        f"미결제약정: {data['open_interest']:,.0f} BTC",
        "",
        f"시장 판단: {mood}",
        f"해석: {interpretation}",
    ]
    return "\n".join(lines)


def main():
    print(build_report())


if __name__ == "__main__":
    main()
