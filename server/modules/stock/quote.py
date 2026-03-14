"""行情数据获取模块 - yfinance + 富途双通道"""
import math
import time
import logging
from threading import Lock

import yfinance as yf
from futu import OpenQuoteContext, RET_OK

from .config import get_futu_host, get_futu_port

logger = logging.getLogger("stock.quote")

# ---------- Simple TTL cache ----------
_cache: dict[str, tuple[float, object, int]] = {}
_cache_lock = Lock()
_CACHE_TTL = 120  # seconds (default)

# ---------- yfinance 请求串行化 ----------
_yf_lock = Lock()


def _cache_get(key: str):
    with _cache_lock:
        entry = _cache.get(key)
        if entry and (time.time() - entry[0]) < entry[2]:
            return entry[1]
    return None


def _cache_set(key: str, value: object, ttl: int = _CACHE_TTL):
    with _cache_lock:
        _cache[key] = (time.time(), value, ttl)


def _safe_float(val, default=0):
    if val is None:
        return default
    try:
        f = float(val)
        return default if math.isnan(f) else f
    except (TypeError, ValueError):
        return default


def to_yf_ticker(code, market="US"):
    ticker = code.upper()
    if market == "HK":
        digits = ticker.lstrip("0") or "0"
        if len(digits) < 4:
            digits = digits.zfill(4)
        ticker = digits + ".HK"
    return ticker


def normalize_full_code(code, market="US"):
    if "." not in code:
        if market == "HK":
            code = code.zfill(5)
        return f"{market}.{code}"
    return code


def fetch_price_yfinance(code, market="US"):
    try:
        ticker = to_yf_ticker(code, market)
        stock = yf.Ticker(ticker)
        info = stock.info
        price = info.get("regularMarketPrice") or info.get("currentPrice")
        val = _safe_float(price)
        return val if val > 0 else None
    except Exception as e:
        logger.error(f"yfinance 获取价格失败 [{code}]: {e}")
        return None


def fetch_price_futu(full_code, quote_ctx=None, host=None, port=None):
    host = host or get_futu_host()
    port = port or get_futu_port()
    created_ctx = False
    try:
        if quote_ctx is None:
            quote_ctx = OpenQuoteContext(host=host, port=port)
            created_ctx = True
        ret, data = quote_ctx.get_market_snapshot([full_code])
        if ret == RET_OK and data is not None and not data.empty:
            val = _safe_float(data.iloc[0]["last_price"])
            return val if val > 0 else None
    except Exception as e:
        logger.error(f"富途获取价格失败 [{full_code}]: {e}")
    finally:
        if created_ctx and quote_ctx is not None:
            quote_ctx.close()
    return None


def fetch_history_yfinance(code, market="US", period="1mo", interval="1d"):
    cache_key = f"hist:{code}:{market}:{period}:{interval}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached
    is_intraday = any(u in interval for u in ("m", "h"))
    try:
        ticker = to_yf_ticker(code, market)
        stock = yf.Ticker(ticker)
        hist = stock.history(period=period, interval=interval)
        if not hist.empty:
            if is_intraday:
                dates = [d.strftime("%Y-%m-%d %H:%M") for d in hist.index]
            else:
                dates = [d.strftime("%Y-%m-%d") for d in hist.index]
            result = {
                "dates": dates,
                "close": hist["Close"].tolist(),
                "high": hist["High"].tolist(),
                "low": hist["Low"].tolist(),
            }
            ttl = 30 if is_intraday else _CACHE_TTL
            _cache_set(cache_key, result, ttl=ttl)
            return result
    except Exception as e:
        logger.error(f"yfinance 获取历史数据失败 [{code}]: {e}")
    return None


def fetch_quotes_batch(tickers, market="US"):
    cache_key = f"quotes_batch:{','.join(sorted(tickers))}:{market}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached
    quotes = {}
    if market == "HK":
        yf_tickers = []
        ticker_map = {}
        for t in tickers:
            digits = t.lstrip("0") or "0"
            if len(digits) < 4:
                digits = digits.zfill(4)
            yf_t = digits + ".HK"
            yf_tickers.append(yf_t)
            ticker_map[yf_t] = t
        symbols = " ".join(yf_tickers)
    else:
        symbols = " ".join(tickers)
        ticker_map = {t: t for t in tickers}

    try:
        batch = yf.Tickers(symbols)
        for yf_sym, orig_sym in ticker_map.items():
            try:
                info = batch.tickers[yf_sym].info
                market_state = info.get("marketState", "CLOSED")
                regular_price = info.get("regularMarketPrice")
                regular_change = info.get("regularMarketChange")
                regular_change_pct = info.get("regularMarketChangePercent")
                prev_close = info.get("previousClose") or info.get("regularMarketPreviousClose")
                pre_price = info.get("preMarketPrice")
                pre_change = info.get("preMarketChange")
                pre_change_pct = info.get("preMarketChangePercent")
                post_price = info.get("postMarketPrice")
                post_change = info.get("postMarketChange")
                post_change_pct = info.get("postMarketChangePercent")

                if market_state == "PRE" and pre_price:
                    current_price = pre_price
                    session = "盘前"
                elif market_state == "POST" and post_price:
                    current_price = post_price
                    session = "盘后"
                elif market_state == "REGULAR" and regular_price:
                    current_price = regular_price
                    session = "盘中"
                else:
                    current_price = regular_price
                    session = "休市"

                quotes[orig_sym] = {
                    "current_price": current_price,
                    "session": session,
                    "regular_price": regular_price,
                    "regular_change": regular_change,
                    "regular_change_pct": regular_change_pct,
                    "pre_price": pre_price,
                    "pre_change": pre_change,
                    "pre_change_pct": pre_change_pct,
                    "post_price": post_price,
                    "post_change": post_change,
                    "post_change_pct": post_change_pct,
                    "prev_close": prev_close,
                }
            except Exception:
                pass
    except Exception:
        pass
    if quotes:
        _cache_set(cache_key, quotes)
    return quotes


def _parse_option_df(df):
    records = []
    for _, row in df.iterrows():
        records.append({
            "contractSymbol": row.get("contractSymbol", ""),
            "strike": _safe_float(row.get("strike")),
            "lastPrice": _safe_float(row.get("lastPrice")),
            "bid": _safe_float(row.get("bid")),
            "ask": _safe_float(row.get("ask")),
            "change": _safe_float(row.get("change")),
            "percentChange": _safe_float(row.get("percentChange")),
            "volume": int(_safe_float(row.get("volume"))),
            "openInterest": int(_safe_float(row.get("openInterest"))),
            "impliedVolatility": _safe_float(row.get("impliedVolatility")),
            "inTheMoney": bool(row.get("inTheMoney", False)),
        })
    return records


def _yf_retry(fn, max_retries=3):
    """Execute a yfinance callable with retry on rate limiting."""
    for attempt in range(max_retries):
        try:
            with _yf_lock:
                return fn()
        except Exception as e:
            if "Too Many Requests" in str(e) and attempt < max_retries - 1:
                wait = 2 ** attempt
                logger.warning(f"yfinance rate limited, retry in {wait}s...")
                time.sleep(wait)
                continue
            raise


def fetch_option_expiry_dates(code, market="US"):
    cache_key = f"opt_expiry:{code}:{market}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached
    try:
        ticker = to_yf_ticker(code, market)

        def _fetch():
            stock = yf.Ticker(ticker)
            return list(stock.options)

        result = _yf_retry(_fetch)
        if result:
            _cache_set(cache_key, result)
        return result
    except Exception as e:
        logger.error(f"获取期权到期日失败 [{code}]: {e}")
        return []


def fetch_option_chain(code, market="US", expiry_date=None):
    cache_key = f"opt_chain:{code}:{market}:{expiry_date}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached
    try:
        ticker = to_yf_ticker(code, market)

        # 优先从缓存获取到期日列表，避免重复请求
        expiry_cache_key = f"opt_expiry:{code}:{market}"
        available_dates = _cache_get(expiry_cache_key)

        if available_dates is None:
            def _fetch_dates():
                s = yf.Ticker(ticker)
                return list(s.options)
            available_dates = _yf_retry(_fetch_dates)
            if available_dates:
                _cache_set(expiry_cache_key, available_dates)

        if not available_dates:
            return None
        if expiry_date is None:
            expiry_date = available_dates[0]
        elif expiry_date not in available_dates:
            return None

        # 更新 cache_key（expiry_date 现在确定了）
        cache_key = f"opt_chain:{code}:{market}:{expiry_date}"
        cached = _cache_get(cache_key)
        if cached is not None:
            return cached

        def _fetch_chain():
            stock = yf.Ticker(ticker)
            chain = stock.option_chain(expiry_date)
            info = stock.info
            return chain, info

        chain, info = _yf_retry(_fetch_chain)
        underlying_price = _safe_float(
            info.get("regularMarketPrice") or info.get("currentPrice")
        )

        result = {
            "code": code,
            "expiry_date": expiry_date,
            "underlying_price": underlying_price,
            "calls": _parse_option_df(chain.calls),
            "puts": _parse_option_df(chain.puts),
        }
        _cache_set(cache_key, result)
        return result
    except Exception as e:
        logger.error(f"获取期权链失败 [{code}] expiry={expiry_date}: {e}")
        return None
