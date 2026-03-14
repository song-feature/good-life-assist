"""技术分析模块 - RSI、MA 计算 + 个股分析"""
import logging
from .quote import fetch_history_yfinance, fetch_option_expiry_dates, fetch_option_chain

logger = logging.getLogger("stock.analysis")


def calc_rsi(closes, period=14):
    if len(closes) < period + 1:
        return None
    deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
    recent = deltas[-period:]
    gains = [d for d in recent if d > 0]
    losses = [-d for d in recent if d < 0]
    avg_gain = sum(gains) / period if gains else 0
    avg_loss = sum(losses) / period if losses else 0
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return round(100 - (100 / (1 + rs)), 2)


def calc_ma(closes, period):
    if len(closes) < period:
        return None
    return round(sum(closes[-period:]) / period, 4)


def calc_ma_series(closes, period):
    """计算移动平均线序列"""
    result = []
    for i in range(len(closes)):
        if i < period - 1:
            result.append(None)
        else:
            window = closes[i - period + 1:i + 1]
            result.append(round(sum(window) / period, 4))
    return result


def analyze_ticker(ticker, market="US", period="1mo", interval="1d"):
    """分析单只股票：价格趋势 + 期权概况"""
    result = {"ticker": ticker}

    hist = fetch_history_yfinance(ticker, market=market, period=period, interval=interval)
    if hist and hist.get("close"):
        closes = hist["close"]
        dates = hist.get("dates", [])
        current = closes[-1] if closes else None
        result["current_price"] = current
        result["dates"] = dates
        result["closes"] = closes
        result["price_5d_ago"] = closes[-6] if len(closes) >= 6 else closes[0]
        result["price_change_5d_pct"] = round(
            (current - result["price_5d_ago"]) / result["price_5d_ago"] * 100, 2
        ) if current and result["price_5d_ago"] else None

        result["ma5"] = calc_ma(closes, 5)
        result["ma20"] = calc_ma(closes, 20)
        result["ma5_series"] = calc_ma_series(closes, 5)
        result["ma20_series"] = calc_ma_series(closes, 20)
        result["rsi14"] = calc_rsi(closes, 14)

        if result["ma5"] and result["ma20"]:
            if result["ma5"] > result["ma20"]:
                result["ma_signal"] = "golden_cross"
            elif result["ma5"] < result["ma20"]:
                result["ma_signal"] = "death_cross"
            else:
                result["ma_signal"] = "neutral"
        else:
            result["ma_signal"] = "insufficient_data"
    else:
        result["current_price"] = None
        result["closes"] = []
        result["dates"] = []
        result["ma_signal"] = "no_data"
        result["rsi14"] = None
        result["ma5_series"] = []
        result["ma20_series"] = []

    # 期权数据 - 仅在默认周期时获取，避免日内请求的额外开销
    if period == "1mo" and interval == "1d":
        try:
            expiry_dates = fetch_option_expiry_dates(ticker, market=market)
            if expiry_dates:
                chain = fetch_option_chain(ticker, market=market, expiry_date=expiry_dates[0])
                if chain:
                    calls = chain.get("calls", [])
                    puts = chain.get("puts", [])
                    calls_oi = sum(c.get("openInterest", 0) for c in calls)
                    puts_oi = sum(p.get("openInterest", 0) for p in puts)
                    pc_ratio = round(puts_oi / calls_oi, 2) if calls_oi > 0 else 0

                    result["options"] = {
                        "expiry_date": expiry_dates[0],
                        "calls_oi": calls_oi,
                        "puts_oi": puts_oi,
                        "put_call_ratio": pc_ratio,
                    }

                    if pc_ratio > 1.0:
                        result["options_sentiment"] = "bearish"
                    elif pc_ratio < 0.7:
                        result["options_sentiment"] = "bullish"
                    else:
                        result["options_sentiment"] = "neutral"
                else:
                    result["options"] = None
                    result["options_sentiment"] = "no_data"
            else:
                result["options"] = None
                result["options_sentiment"] = "no_options"
        except Exception as e:
            result["options"] = None
            result["options_sentiment"] = f"error: {e}"

    return result
