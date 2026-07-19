"""
v2 메인 스크립트 (Sprint 1-1~1-2: Binance Futures 데이터 엔진 + 롱/숏 스코어 + AI 해석)

market.py에서 가져온 Binance Futures 데이터(시세/펀딩비/미결제약정/OI변화율)를 바탕으로
-100(강한 숏 우세) ~ +100(강한 롱 우세) 스코어를 계산하고, ANTHROPIC_API_KEY가 설정돼
있으면 Claude API로 자연어 해석 문단까지 생성한다. 아직 텔레그램 발송은 하지 않고
콘솔에 출력만 한다 (v1이 계속 매일 7시 발송을 담당하고, v2는 완성되면 이어받을 예정).

환경변수:
    ANTHROPIC_API_KEY (선택) - 없으면 규칙 기반 해석 문장으로 자동 대체됨.
"""

import os

from market import get_market_data


def calculate_score(data):
    """펀딩비, 24h 가격 모멘텀, 미결제약정 변화를 종합해
    -100(강한 숏 우세) ~ +100(강한 롱 우세) 사이의 스코어를 산출한다.

    구성 요소:
    - 펀딩비 점수 (±40점): 펀딩비가 플러스면 롱이 숏에게 수수료를 지불 중 = 롱 우세 신호
    - 가격 모멘텀 점수 (±30점): 24h 변동률
    - 미결제약정 점수 (±30점): OI가 늘면서 가격이 오르면 신규 롱 유입(가산),
      OI가 늘면서 가격이 내리면 신규 숏 유입(감산)
    """
    funding = data["funding"]
    change = data["change"]
    oi_change = data.get("oi_change_24h", 0.0)

    funding_score = max(-40, min(40, (funding / 0.001) * 40))
    momentum_score = max(-30, min(30, (change / 5) * 30))

    oi_score = max(-30, min(30, (oi_change / 10) * 30))
    if change < 0:
        oi_score = -oi_score

    total = funding_score + momentum_score + oi_score
    return round(max(-100, min(100, total)), 1)


def score_label(score):
    if score >= 50:
        return "강한 롱 우세"
    elif score >= 15:
        return "롱 우세"
    elif score <= -50:
        return "강한 숏 우세"
    elif score <= -15:
        return "숏 우세"
    else:
        return "중립"


def rule_based_note(data, score):
    """스코어 기반 규칙 해석 문장 (AI 미사용 시 폴백)."""
    label = score_label(score)
    oi_change = data.get("oi_change_24h", 0.0)

    if label == "강한 롱 우세":
        return f"펀딩비·모멘텀·미결제약정이 모두 롱 쪽으로 쏠려있어({score:+.1f}점) 단기 과열·조정 가능성에 유의하세요."
    elif label == "강한 숏 우세":
        return f"펀딩비·모멘텀·미결제약정이 모두 숏 쪽으로 쏠려있어({score:+.1f}점) 숏스퀴즈(급반등) 가능성에 유의하세요."
    elif label == "롱 우세":
        return f"롱 포지션이 다소 우세합니다({score:+.1f}점). 미결제약정 24h 변화율은 {oi_change:+.1f}%입니다."
    elif label == "숏 우세":
        return f"숏 포지션이 다소 우세합니다({score:+.1f}점). 미결제약정 24h 변화율은 {oi_change:+.1f}%입니다."
    else:
        return f"뚜렷한 쏠림 없이 중립 범위입니다({score:+.1f}점)."


def _build_prompt(data, score, label):
    return (
        "다음은 비트코인 무기한 선물(Binance) 데이터입니다.\n"
        f"- 현재가: {data['price']:,.0f} USDT\n"
        f"- 24시간 변동률: {data['change']:+.2f}%\n"
        f"- 24시간 거래대금: {data['volume']:,.0f} USDT\n"
        f"- 펀딩비: {data['funding']:.5f}\n"
        f"- 미결제약정: {data['open_interest']:,.0f} BTC\n"
        f"- 미결제약정 24h 변화율: {data.get('oi_change_24h', 0.0):+.1f}%\n"
        f"- 롱/숏 스코어: {score:+.1f} (-100 강한 숏 우세 ~ +100 강한 롱 우세)\n"
        f"- 규칙 기반 판단: {label}\n\n"
        "위 데이터를 바탕으로 2~3문장으로 오늘의 시장 분위기와 주의할 점을 "
        "한국어로 간결하게 설명해줘. 투자 조언이 아니라 참고용 해설 톤을 유지해."
    )


def _gemini_interpretation(prompt):
    """GEMINI_API_KEY(무료 티어)로 자연어 해석을 생성한다.
    Google의 신규 Interactions API(v1beta/interactions)를 사용한다.
    (구버전 v1beta/models/{model}:generateContent 엔드포인트는 최근 발급된
    키/프로젝트에서 404가 나서 더 이상 사용하지 않음.) 실패 시 None 반환."""
    import requests

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return None

    url = "https://generativelanguage.googleapis.com/v1beta/interactions"
    resp = requests.post(
        url,
        headers={"x-goog-api-key": api_key, "Content-Type": "application/json"},
        json={"model": "gemini-3.5-flash", "input": prompt},
        timeout=15,
    )
    resp.raise_for_status()
    result = resp.json()

    texts = []
    for step in result.get("steps", []):
        if step.get("type") != "model_output":
            continue
        for item in step.get("content", []):
            if item.get("type") == "text":
                texts.append(item["text"])

    combined = "\n".join(texts).strip()
    return combined or None


def _claude_interpretation(prompt):
    """ANTHROPIC_API_KEY(유료)로 자연어 해석을 생성한다. 실패 시 None 반환."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return None

    import anthropic

    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=300,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text.strip()


def ai_interpretation(data, score, label, note):
    """무료 티어인 GEMINI_API_KEY를 우선 사용하고, 없으면 ANTHROPIC_API_KEY(유료)를
    시도한다. 둘 다 없거나 호출에 실패하면 규칙 기반 문장(note)을 그대로 반환한다."""
    prompt = _build_prompt(data, score, label)

    for name, fn in (("Gemini", _gemini_interpretation), ("Claude", _claude_interpretation)):
        try:
            result = fn(prompt)
            if result:
                return result
        except Exception as e:  # API 실패 시 다음 후보로 조용히 폴백
            print(f"[{name} 해석 실패] {e}")

    return note


def send_telegram_message(text):
    """TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID 환경변수를 이용해 텔레그램으로 전송한다.
    (v1의 daily_btc_report.py와 동일한 Secrets를 재사용 가능)"""
    import requests

    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        print("[텔레그램 미전송] TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID 환경변수가 없습니다.")
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    resp = requests.post(
        url,
        data={"chat_id": chat_id, "text": text, "disable_web_page_preview": True},
        timeout=10,
    )
    resp.raise_for_status()
    return True


def build_report(symbol="BTCUSDT"):
    data = get_market_data(symbol)
    score = calculate_score(data)
    label = score_label(score)
    note = rule_based_note(data, score)
    interpretation = ai_interpretation(data, score, label, note)

    lines = [
        f"📈 {symbol} Futures 리포트 (v2)",
        "",
        f"현재가: {data['price']:,.0f} USDT",
        f"24h 변동: {data['change']:+.2f}%",
        f"24h 거래대금: {data['volume']:,.0f} USDT",
        f"펀딩비: {data['funding']:.5f}",
        f"미결제약정: {data['open_interest']:,.0f} BTC",
        f"미결제약정 24h 변화: {data.get('oi_change_24h', 0.0):+.1f}%",
        "",
        f"롱/숏 스코어: {score:+.1f} ({label})",
        f"해석: {interpretation}",
    ]
    return "\n".join(lines)


def main():
    report = build_report()
    print(report)
    print()
    if send_telegram_message(report):
        print("[텔레그램 전송 완료]")


if __name__ == "__main__":
    main()
