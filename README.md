# 비트코인 데일리 텔레그램 브리핑 — 설정 가이드

PC를 켜둘 필요 없이, **GitHub Actions**가 매일 아침 7시(KST)에 클라우드에서
자동으로 비트코인 시세 + 지지/저항선 + 국내외 뉴스를 텔레그램으로 보내줍니다.

---

## 1. 텔레그램 봇 만들기 (3분)

1. 텔레그램 앱에서 **@BotFather** 검색 후 대화 시작
2. `/newbot` 입력
3. 봇 이름 입력 (예: `BTC Daily Report`)
4. 봇 username 입력 (예: `my_btc_daily_bot`, 끝에 `bot`이 들어가야 함)
5. 완료되면 **토큰**이 발급됩니다 (`123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ` 형태)
   → 이게 `TELEGRAM_BOT_TOKEN`

## 2. 내 chat_id 알아내기

1. 방금 만든 봇을 텔레그램에서 검색해서 **대화 시작** (아무 메시지나 전송, 예: "안녕")
2. 브라우저에서 아래 주소 접속 (BOT_TOKEN 부분을 본인 토큰으로 교체)
