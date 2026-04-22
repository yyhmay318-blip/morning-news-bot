import os, requests, feedparser, urllib3
from datetime import datetime
urllib3.disable_warnings()

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]

RSS_FEEDS = [
    ("연합뉴스", "https://www.yna.co.kr/rss/economy.xml"),
    ("이데일리",  "https://rss.edaily.co.kr/edaily/stock.xml"),
    ("한국경제",  "https://www.hankyung.com/feed/finance"),
    ("매일경제",  "https://www.mk.co.kr/rss/30000001/"),
]

def get_headlines():
    headlines = []
    for name, url in RSS_FEEDS:
        try:
            feed = feedparser.parse(url, request_headers={"User-Agent": "Mozilla/5.0"})
            for entry in feed.entries[:8]:
                headlines.append(entry.title)
            print(f"  [{name}]: {len(feed.entries[:8])}건")
        except Exception as e:
            print(f"  [{name}] 오류: {e}")
    return headlines

def get_stock_prices():
    try:
        import yfinance as yf
        tickers = {
            "코스피": "^KS11", "코스닥": "^KQ11",
            "S&P500": "^GSPC", "나스닥": "^IXIC",
            "삼성전자": "005930.KS", "SK하이닉스": "000660.KS",
            "비트코인": "BTC-USD", "이더리움": "ETH-USD",
        }
        prices = {}
        for name, symbol in tickers.items():
            try:
                hist = yf.Ticker(symbol).history(period="2d")
                if len(hist) >= 1:
                    cur = hist["Close"].iloc[-1]
                    if len(hist) >= 2:
                        pct = (cur - hist["Close"].iloc[-2]) / hist["Close"].iloc[-2] * 100
                        prices[name] = f"{cur:,.0f} ({pct:+.1f}%)"
                    else:
                        prices[name] = f"{cur:,.0f}"
            except: pass
        return prices
    except: return {}

def summarize_with_gemini(headlines, prices):
    today = datetime.now().strftime("%Y년 %m월 %d일")
    price_text = "\n".join(f"- {k}: {v}" for k, v in prices.items()) or "- (없음)"
    headline_text = "\n".join(f"- {h}" for h in headlines[:25])
    prompt = f"""오늘 한국 금융시장 모닝 브리핑을 작성해주세요.

📊 주요 시세:
{price_text}

📰 뉴스 헤드라인:
{headline_text}

아래 형식으로 한국어 작성 (각 섹터 2~3줄, 수치 포함):

📰 모닝 마켓 브리핑
{today} 오전 8:30

🔬 반도체
(요약)

🚢 조선
(요약)

☀️ 재생에너지
(요약)

📈 미국/한국 증시
(코스피·코스닥·나스닥·S&P500 수치 포함)

🪙 코인
(비트코인·이더리움 시세 포함)

💡 오늘의 한마디
(한 문장)"""

    resp = requests.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}",
        json={"contents": [{"parts": [{"text": prompt}]}]},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["candidates"][0]["content"]["parts"][0]["text"]

def send_telegram(message):
    resp = requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
        data={"chat_id": TELEGRAM_CHAT_ID, "text": message},
        timeout=15,
    )
    return resp.json().get("ok", False)

print("뉴스 수집 중...")
headlines = get_headlines()
print(f"총 {len(headlines)}개\n")
print("시세 조회 중...")
prices = get_stock_prices()
print("AI 요약 중...")
message = summarize_with_gemini(headlines, prices)
print("텔레그램 발송 중...")
print("성공!" if send_telegram(message) else "실패")
