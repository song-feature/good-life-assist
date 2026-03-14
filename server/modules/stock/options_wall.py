"""期权墙算法 - 周五到期日解析、Top OI 行权价、Max Pain 计算"""
import logging
from datetime import date, timedelta

from .quote import fetch_option_expiry_dates, fetch_option_chain

logger = logging.getLogger("stock.options_wall")


def resolve_friday_expiries(available_dates: list[str]) -> dict:
    """从可用到期日列表中找出本周五和下周五对应的 expiry date。

    规则：
    - 若今天是周六/日，"本周五"视为下周五
    - 在 available_dates 中找精确匹配或最近的不早于目标日期的到期日
    """
    today = date.today()
    weekday = today.weekday()  # Mon=0 ... Sun=6

    # 计算本周五
    if weekday <= 4:  # Mon–Fri
        this_fri = today + timedelta(days=(4 - weekday))
    else:  # Sat/Sun → 下周五
        this_fri = today + timedelta(days=(11 - weekday))

    next_fri = this_fri + timedelta(days=7)

    sorted_dates = sorted(available_dates)

    def find_nearest(target: date) -> str | None:
        target_str = target.isoformat()
        # 精确匹配
        if target_str in sorted_dates:
            return target_str
        # 找最近的不早于 target 的日期
        for d in sorted_dates:
            if d >= target_str:
                return d
        return None

    return {
        "this_friday": find_nearest(this_fri),
        "next_friday": find_nearest(next_fri),
    }


def compute_max_pain(calls: list[dict], puts: list[dict]) -> float | None:
    """计算 Max Pain（使期权买方总亏损最大的行权价）。

    pain(S) = Σ(call_OI × max(0, S - K_call)) + Σ(put_OI × max(0, K_put - S))
    返回使 pain 最小的 S。
    """
    all_strikes = sorted(set(
        [c["strike"] for c in calls if c.get("strike")]
        + [p["strike"] for p in puts if p.get("strike")]
    ))
    if not all_strikes:
        return None

    min_pain = float("inf")
    max_pain_strike = all_strikes[0]

    for s in all_strikes:
        pain = 0.0
        for c in calls:
            oi = c.get("openInterest", 0) or 0
            pain += oi * max(0.0, s - c["strike"])
        for p in puts:
            oi = p.get("openInterest", 0) or 0
            pain += oi * max(0.0, p["strike"] - s)
        if pain < min_pain:
            min_pain = pain
            max_pain_strike = s

    return round(max_pain_strike, 2)


def compute_options_wall(chain: dict, top_n: int = 5) -> dict | None:
    """从期权链中提取期权墙数据。

    call_walls = Top N 看涨 OI 行权价（阻力位）
    put_walls  = Top N 看跌 OI 行权价（支撑位）
    """
    if not chain:
        return None

    calls = chain.get("calls", [])
    puts = chain.get("puts", [])

    def top_oi(options: list[dict], n: int) -> list[dict]:
        valid = [o for o in options if (o.get("openInterest") or 0) > 0]
        valid.sort(key=lambda x: x.get("openInterest", 0), reverse=True)
        return [
            {
                "strike": round(o["strike"], 2),
                "openInterest": o.get("openInterest", 0),
                "volume": o.get("volume", 0) or 0,
            }
            for o in valid[:n]
        ]

    total_calls_oi = sum(c.get("openInterest", 0) or 0 for c in calls)
    total_puts_oi = sum(p.get("openInterest", 0) or 0 for p in puts)
    pc_ratio = round(total_puts_oi / total_calls_oi, 2) if total_calls_oi > 0 else 0.0

    return {
        "expiry_date": chain.get("expiry_date", ""),
        "underlying_price": chain.get("underlying_price", 0),
        "call_walls": top_oi(calls, top_n),
        "put_walls": top_oi(puts, top_n),
        "max_pain": compute_max_pain(calls, puts),
        "total_calls_oi": total_calls_oi,
        "total_puts_oi": total_puts_oi,
        "put_call_ratio": pc_ratio,
    }


def get_options_wall_for_ticker(code: str, market: str = "US") -> dict:
    """编排函数：获取到期日 → 解析周五 → 分别拉链 → 计算墙"""
    result: dict = {"ticker": code, "current_price": None, "this_friday": None, "next_friday": None}

    try:
        expiry_dates = fetch_option_expiry_dates(code, market=market)
    except Exception as e:
        logger.warning(f"获取 {code} 期权到期日失败: {e}")
        return result

    if not expiry_dates:
        logger.info(f"{code} 无可用期权到期日")
        return result

    fridays = resolve_friday_expiries(expiry_dates)

    for key in ("this_friday", "next_friday"):
        expiry = fridays.get(key)
        if not expiry:
            continue
        try:
            chain = fetch_option_chain(code, market=market, expiry_date=expiry)
            if chain:
                if result["current_price"] is None:
                    result["current_price"] = chain.get("underlying_price")
                result[key] = compute_options_wall(chain)
        except Exception as e:
            logger.warning(f"获取 {code} 期权链 ({expiry}) 失败: {e}")

    return result
