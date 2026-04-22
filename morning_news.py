import os, requests, feedparser, urllib3
from datetime import datetime
urllib3.disable_warnings()
TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
RSS_FEEDS = [
    ("연합뉴스", "https://www.yna.co.kr/rss/economy.xml"),
    ("한국경제", "https://www.hankyung.com/feed/finance"),
    ("매일경제", "https://www.mk.co.kr/rss/30000001/"),
]
def get_headlines():
    headlines = []
    for name, url in RSS_FEEDS:
        try:
            feed = feedparser.parse(url, request_headers={"User-Agent": "Mozilla/5.0"})
            for entry in feed.entries[:8]:
                headlines.append(entry.title)
        except: pass
    return headlines
def get_stock_prices():
    try:
        import yfinance as yf
        tickers = {"코스피":"^KS11","코스닥":"^KQ11","S&P500":"^GSPC","나스닥":"^IXIC","비트코인":"BTC-USD","이더리움":"ETH-USD"}
        prices = {}
        for name, symbol in tickers.items():
            try:
                hist = yf.Ticker(symbol).history(period="2d")
                if len(hist) >= 2:
                    cur, prev = hist["Close"].iloc[-1], hist["Close"].iloc[-2]
                    pct = (cur - prev) / prev * 100
                    prices[name] = f"{cur:,.0f} ({pct:+.1f}%)"
            except: pass
        return prices
    except: return {}
def summarize(headlines, prices):
    today = datetime.now().strftime("%Y년 %m월 %d일")
    price_text = "\n".join(f"- {k}: {v}" for k, v in prices.items()) or "- 데이터 없음"
    headline_text = "\n".join(f"- {h}" for h in headlines[:20])
    prompt = f"""한국 금융 모닝 브리핑 작성. 아래 형식 그대로:

📰 모닝 마켓 브리핑
{today} 오전 8:30

🔬 반도체
(2~3줄)

🚢 조선
(2~3줄)

☀️ 재생에너지
(2~3줄)

📈 미국/한국 증시
(수치 포함 2~3줄)

🪙 코인
(수치 포함 2~3줄)

💡 오늘의 한마디
(한 문장)

참고 시세:
{price_text}

참고 뉴스:
{headline_text}"""
    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
    r = requests.post(f"{url}?key={GEMINI_API_KEY}", json={"contents":[{"parts":[{"text":prompt}]}]}, timeout=30)
    r.raise_for_status()
    return r.json()["candidates"][0]["content"]["parts"][0]["text"]
def send_telegram(msg):
    r = requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", data={"chat_id":TELEGRAM_CHAT_ID,"text":msg}, timeout=15)
    return r.json().get("ok", False)
print("시작!")
h = get_headlines()
p = get_stock_prices()
msg = summarize(h, p)
ok = send_telegram(msg)
print("성공!" if ok else "실패")
