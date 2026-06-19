import datetime as dt
import math
import os
import sys
from dataclasses import dataclass
from typing import Any
from zoneinfo import ZoneInfo

import requests
import yfinance as yf

PACIFIC = ZoneInfo("America/Los_Angeles")
EASTERN = ZoneInfo("America/New_York")

FIXED_TICKERS = ["SPY", "NVDA", "TSLA", "SOFI"]

DEFAULT_MOVER_TICKERS = [
    "QQQ", "IWM", "AAPL", "MSFT", "AMD", "META", "AMZN", "GOOGL", "NFLX", "AVGO",
    "COIN", "MSTR", "PLTR", "SMCI", "HOOD", "SHOP", "BABA", "RIVN", "LCID", "MARA",
    "RIOT", "AFRM", "SNOW", "CRWD", "UBER", "NIO", "XPEV", "MRVL", "MU", "ARM",
]

MARKET_HOLIDAYS = {
    dt.date(2026, 1, 1), dt.date(2026, 1, 19), dt.date(2026, 2, 16), dt.date(2026, 4, 3),
    dt.date(2026, 5, 25), dt.date(2026, 6, 19), dt.date(2026, 7, 3), dt.date(2026, 9, 7),
    dt.date(2026, 11, 26), dt.date(2026, 12, 25), dt.date(2027, 1, 1), dt.date(2027, 1, 18),
    dt.date(2027, 2, 15), dt.date(2027, 3, 26), dt.date(2027, 5, 31), dt.date(2027, 6, 18),
    dt.date(2027, 7, 5), dt.date(2027, 9, 6), dt.date(2027, 11, 25), dt.date(2027, 12, 24),
}


@dataclass
class Candidate:
    ticker: str
    price: float
    pct_change: float
    rvol: float
    catalyst: str
    risk: str
    direction: str
    grade: str
    score: int
    event: str
    setup: str
    news: str


def env(name: str, default: str = "") -> str:
    value = os.getenv(name)
    if value is None or not value.strip():
        return default
    return value.strip()


def safe_int(value: str, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        value = float(value)
        return default if math.isnan(value) else value
    except Exception:
        return default


def is_trading_day() -> bool:
    today = dt.datetime.now(PACIFIC).date()
    return today.weekday() < 5 and today not in MARKET_HOLIDAYS


def fmt_pct(value: float) -> str:
    return f"{value:+.1f}%"


def price_snapshot(symbol: str) -> tuple[float, float, float]:
    ticker = yf.Ticker(symbol)
    price = prev_close = avg_volume = 0.0

    try:
        info = ticker.fast_info or {}
        price = safe_float(info.get("last_price") or info.get("lastPrice"))
        prev_close = safe_float(info.get("previous_close") or info.get("previousClose"))
        avg_volume = safe_float(info.get("ten_day_average_volume") or info.get("three_month_average_volume"))
    except Exception:
        pass

    try:
        history = ticker.history(period="3mo", interval="1d", auto_adjust=False)
    except Exception:
        history = None

    if history is not None and not history.empty:
        if price <= 0:
            price = safe_float(history["Close"].iloc[-1])
        if prev_close <= 0 and len(history) >= 2:
            prev_close = safe_float(history["Close"].iloc[-2])
        if avg_volume <= 0:
            avg_volume = safe_float(history["Volume"].tail(20).mean())

    pct_change = ((price - prev_close) / prev_close * 100) if prev_close > 0 else 0.0
    return price, pct_change, avg_volume


def relative_volume(symbol: str, avg_daily_volume: float) -> float:
    if avg_daily_volume <= 0:
        return 0.0
    try:
        bars = yf.Ticker(symbol).history(period="2d", interval="1m", prepost=True, auto_adjust=False)
    except Exception:
        return 0.0
    if bars.empty:
        return 0.0
    today_et = dt.datetime.now(EASTERN).date()
    rows = bars[bars.index.tz_convert(EASTERN).date == today_et]
    return safe_float(rows["Volume"].sum()) / avg_daily_volume if not rows.empty else 0.0


def catalyst(symbol: str) -> str:
    try:
        news = yf.Ticker(symbol).news or []
    except Exception:
        news = []
    if not news:
        return "未找到明显新闻催化"
    title = news[0].get("title") or news[0].get("content", {}).get("title") or "有最新相关新闻"
    return title[:120]


def direction(pct_change: float, rvol: float) -> str:
    if pct_change >= 1.0 and rvol >= 0.03:
        return "Call"
    if pct_change <= -1.0 and rvol >= 0.03:
        return "Put"
    return "Watch"


def risk(pct_change: float, rvol: float) -> str:
    if abs(pct_change) >= 7 or rvol >= 0.25:
        return "High"
    if abs(pct_change) >= 3 or rvol >= 0.10:
        return "Medium"
    return "Low"


def grade(score: int) -> str:
    if score >= 85:
        return "A+"
    if score >= 70:
        return "A"
    if score >= 55:
        return "B"
    if score >= 40:
        return "C"
    return "D"


def build_reason(pct_change: float, rvol: float, direction_label: str, headline: str) -> tuple[str, str, str]:
    if pct_change >= 3:
        event = f"价格上涨 {fmt_pct(pct_change)}，属于明显跳涨/强势异动"
    elif pct_change >= 1:
        event = f"价格上涨 {fmt_pct(pct_change)}，短线偏强"
    elif pct_change <= -3:
        event = f"价格下跌 {fmt_pct(pct_change)}，属于明显跳水/弱势异动"
    elif pct_change <= -1:
        event = f"价格下跌 {fmt_pct(pct_change)}，短线偏弱"
    else:
        event = f"价格涨跌幅 {fmt_pct(pct_change)}，暂时没有明显单边方向"

    if rvol >= 0.15:
        volume = f"RVOL {rvol:.2f}，盘前/当日成交显著放大"
    elif rvol >= 0.05:
        volume = f"RVOL {rvol:.2f}，成交量比平时更活跃"
    elif rvol > 0:
        volume = f"RVOL {rvol:.2f}，成交量暂时一般"
    else:
        volume = "RVOL 暂无有效数据"

    if direction_label == "Call":
        setup = f"{volume}；价格强于昨收且成交配合，偏 Call 观察"
    elif direction_label == "Put":
        setup = f"{volume}；价格弱于昨收且成交配合，偏 Put 观察"
    else:
        setup = f"{volume}；方向还不够明确，先列入 Watch"

    if headline != "未找到明显新闻催化":
        news = headline[:90]
    else:
        news = "未发现明确新闻催化"

    return event, setup, news


def analyze(symbol: str) -> Candidate | None:
    price, pct_change, avg_volume = price_snapshot(symbol)
    if price <= 0:
        return None

    rvol = relative_volume(symbol, avg_volume)
    headline = catalyst(symbol)
    has_catalyst = headline != "未找到明显新闻催化"
    score = min(45, int(abs(pct_change) * 7)) + min(40, int(rvol * 180))
    if has_catalyst:
        score += 15
    score = min(score, 100)
    dir_label = direction(pct_change, rvol)
    event, setup, news = build_reason(pct_change, rvol, dir_label, headline)

    return Candidate(
        ticker=symbol,
        price=price,
        pct_change=pct_change,
        rvol=rvol,
        catalyst=headline,
        risk=risk(pct_change, rvol),
        direction=dir_label,
        grade=grade(score),
        score=score,
        event=event,
        setup=setup,
        news=news,
    )


def analyze_many(tickers: list[str]) -> list[Candidate]:
    candidates = []
    for symbol in tickers:
        try:
            candidate = analyze(symbol)
            if candidate:
                candidates.append(candidate)
        except Exception as exc:
            print(f"{symbol}: {exc}", file=sys.stderr)
    return candidates


def section_header(title: str, subtitle: str) -> list[str]:
    bar = "════════════════════"
    return [bar, title, subtitle, bar, ""]


def format_candidate(item: Candidate, prefix: str = "") -> list[str]:
    direction_labels = {"Call": "Call", "Put": "Put", "Watch": "Watch"}
    direction_icons = {"Call": "🟢", "Put": "🔴", "Watch": "🟡"}
    risk_labels = {"High": "高", "Medium": "中", "Low": "低"}
    label = f"{prefix}{item.ticker}" if prefix else item.ticker
    return [
        f"{direction_icons[item.direction]} **{label} | {item.grade} | {direction_labels[item.direction]} | 0DTE: {item.score}/100**",
        f"价格: `${item.price:.2f}` | 涨跌: `{fmt_pct(item.pct_change)}`",
        f"RVOL: `{item.rvol:.2f}` | 风险: `{risk_labels[item.risk]}`",
        f"发生: {item.event}",
        f"判断: {item.setup}",
        f"新闻: {item.news}",
        "",
    ]


def format_message(fixed: list[Candidate], movers: list[Candidate]) -> str:
    now = dt.datetime.now(PACIFIC).strftime("%I:%M %p PT")
    lines = [
        "📈 **Daily Options Watchlist**",
        f"🕒 `{now}`",
        "`格式版本: reason-v2`",
        "",
        "仅供盘中/短线期权观察，不构成投资建议。",
        "",
    ]

    lines += section_header("⭐ **FIXED WATCHLIST**", "重点关注")
    if fixed:
        for item in fixed:
            lines += format_candidate(item)
    else:
        lines += ["固定观察名单暂时没有可用数据。", ""]

    lines += section_header("🔥 **HIGH-VOLATILITY MOVERS**", "随机异动股")
    if movers:
        number_icons = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
        for index, item in enumerate(movers):
            prefix = f"{number_icons[index]} " if index < len(number_icons) else f"{index + 1}. "
            lines += format_candidate(item, prefix)
    else:
        lines += ["暂时没有发现额外高波动异动股。", ""]

    return "\n".join(lines).strip()


def split_discord_message(content: str, limit: int = 1800) -> list[str]:
    chunks = []
    current = ""
    for line in content.splitlines():
        addition = line + "\n"
        if len(current) + len(addition) > limit:
            if current.strip():
                chunks.append(current.strip())
            current = addition
        else:
            current += addition
    if current.strip():
        chunks.append(current.strip())
    return chunks


def post_discord(webhook_url: str, content: str) -> None:
    response = requests.post(webhook_url, json={"content": content}, timeout=30)
    if response.status_code >= 300:
        raise RuntimeError(f"Discord webhook failed: {response.status_code} {response.text}")


def post_discord_message(webhook_url: str, content: str) -> None:
    chunks = split_discord_message(content)
    total = len(chunks)
    for index, chunk in enumerate(chunks, 1):
        if total > 1:
            chunk = f"{chunk}\n\n`第 {index}/{total} 段`"
        post_discord(webhook_url, chunk)


def main() -> int:
    webhook_url = env("DISCORD_WEBHOOK_URL")
    if not webhook_url:
        print("缺少 DISCORD_WEBHOOK_URL。", file=sys.stderr)
        return 2

    if env("SKIP_TRADING_DAY_CHECK", "false").lower() not in {"1", "true", "yes"} and not is_trading_day():
        print("今天不是美股交易日，跳过。")
        return 0

    mover_text = env("WATCHLIST_TICKERS", ",".join(DEFAULT_MOVER_TICKERS))
    mover_tickers = [t.strip().upper() for t in mover_text.split(",") if t.strip()]
    fixed_set = set(FIXED_TICKERS)
    mover_tickers = [t for t in mover_tickers if t not in fixed_set]
    max_movers = safe_int(env("MAX_RESULTS", "8"), 8)

    fixed = analyze_many(FIXED_TICKERS)
    movers = analyze_many(mover_tickers)
    movers.sort(key=lambda c: (c.score, abs(c.pct_change), c.rvol), reverse=True)
    movers = movers[:max_movers]

    post_discord_message(webhook_url, format_message(fixed, movers))
    print(f"已发送固定观察 {len(fixed)} 个，异动股 {len(movers)} 个。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
