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

DEFAULT_TICKERS = [
    "SPY", "QQQ", "IWM", "AAPL", "MSFT", "NVDA", "AMD", "TSLA", "META", "AMZN",
    "GOOGL", "NFLX", "AVGO", "COIN", "MSTR", "PLTR", "SMCI", "HOOD", "SHOP", "BABA",
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

    history = ticker.history(period="3mo", interval="1d", auto_adjust=False)
    if not history.empty:
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
    return title[:140]


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


def analyze(symbol: str) -> Candidate | None:
    price, pct_change, avg_volume = price_snapshot(symbol)
    if price <= 0:
        return None
    rvol = relative_volume(symbol, avg_volume)
    headline = catalyst(symbol)
    score = min(45, int(abs(pct_change) * 7)) + min(40, int(rvol * 180))
    if headline != "未找到明显新闻催化":
        score += 15
    score = min(score, 100)
    return Candidate(symbol, price, pct_change, rvol, headline, risk(pct_change, rvol), direction(pct_change, rvol), grade(score), score)


def format_message(candidates: list[Candidate]) -> str:
    now = dt.datetime.now(PACIFIC).strftime("%Y-%m-%d %I:%M %p PT")
    lines = [
        "**每日短线期权观察名单**",
        f"`{now}`",
        "",
        "仅供盘中/短线期权观察使用，不构成投资建议，不自动交易，不下单。",
        "",
    ]
    if not candidates:
        lines.append("今天暂时没有筛选出强候选标的。")
        return "\n".join(lines)

    direction_labels = {"Call": "看涨 / Call", "Put": "看跌 / Put", "Watch": "观察 / Watch"}
    risk_labels = {"High": "高", "Medium": "中", "Low": "低"}
    for i, item in enumerate(candidates, 1):
        lines += [
            f"**{i}. {item.ticker} | 评级: {item.grade} | 方向: {direction_labels[item.direction]} | 风险: {risk_labels[item.risk]}**",
            f"价格: `${item.price:.2f}` | 涨跌幅: `{fmt_pct(item.pct_change)}` | 相对成交量RVOL: `{item.rvol:.2f}`",
            f"催化/新闻: {item.catalyst}",
            "",
        ]
    return "\n".join(lines).strip()


def post_discord(webhook_url: str, content: str) -> None:
    response = requests.post(webhook_url, json={"content": content}, timeout=30)
    if response.status_code >= 300:
        raise RuntimeError(f"Discord webhook failed: {response.status_code} {response.text}")


def main() -> int:
    webhook_url = env("DISCORD_WEBHOOK_URL")
    if not webhook_url:
        print("缺少 DISCORD_WEBHOOK_URL。", file=sys.stderr)
        return 2

    if env("SKIP_TRADING_DAY_CHECK", "false").lower() not in {"1", "true", "yes"} and not is_trading_day():
        print("今天不是美股交易日，跳过。")
        return 0

    ticker_text = env("WATCHLIST_TICKERS", ",".join(DEFAULT_TICKERS))
    tickers = [t.strip().upper() for t in ticker_text.split(",") if t.strip()]
    max_results = safe_int(env("MAX_RESULTS", "8"), 8)

    candidates = []
    for symbol in tickers:
        try:
            candidate = analyze(symbol)
            if candidate:
                candidates.append(candidate)
        except Exception as exc:
            print(f"{symbol}: {exc}", file=sys.stderr)

    candidates.sort(key=lambda c: (c.score, abs(c.pct_change), c.rvol), reverse=True)
    selected = candidates[:max_results]
    post_discord(webhook_url, format_message(selected))
    print(f"已发送 {len(selected)} 个候选标的: {', '.join(c.ticker for c in selected) or '无'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
