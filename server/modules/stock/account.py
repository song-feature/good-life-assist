"""账户信息模块 - 持仓和资金查询"""
import logging
from futu import RET_OK, TrdMarket, Currency

from .connection import get_connection_manager
from .enums import to_trd_env, to_trd_market
from .config import get_default_market, get_default_env
from .utils import safe_float, safe_int

logger = logging.getLogger("stock.account")


def _market_str(market):
    return "HK" if market == TrdMarket.HK else "US"


def _market_currency(market):
    return Currency.HKD if market == TrdMarket.HK else Currency.USD


def get_positions(market=None, env=None, include_zero=False):
    market = to_trd_market(market or get_default_market())
    env = to_trd_env(env or get_default_env())
    mkt = _market_str(market)
    prefix = f"{mkt}."

    conn_mgr = get_connection_manager()
    ctx = conn_mgr.get_trade_context(market, env)
    acc_id = conn_mgr.get_acc_id(market, env)

    try:
        ret, pos_data = ctx.position_list_query(
            trd_env=env, acc_id=acc_id, refresh_cache=True
        )
        if ret != RET_OK:
            return {"success": False, "error_msg": str(pos_data)}

        positions = []
        today_pl_total = 0.0

        if pos_data is not None and not pos_data.empty:
            for _, row in pos_data.iterrows():
                code = row.get("code", "")
                if not code.startswith(prefix):
                    continue
                today_pl = safe_float(row.get("today_pl_val"))
                today_pl_total += today_pl
                qty = safe_int(row.get("qty"))
                if qty <= 0 and not include_zero:
                    continue
                ticker = code.split(".", 1)[1] if "." in code else code
                positions.append({
                    "code": code,
                    "ticker": ticker,
                    "name": row.get("stock_name", ""),
                    "qty": qty,
                    "can_sell_qty": safe_int(row.get("can_sell_qty")),
                    "cost_price": safe_float(row.get("cost_price")),
                    "market_val": safe_float(row.get("market_val")),
                    "pl_val": safe_float(row.get("pl_val")),
                    "pl_ratio": safe_float(row.get("pl_ratio")),
                    "today_pl_val": today_pl,
                })

        return {
            "success": True,
            "positions": positions,
            "today_pl_total": today_pl_total,
        }
    except Exception as e:
        logger.error(f"获取持仓失败 [{mkt}]: {e}")
        return {"success": False, "error_msg": str(e)}


def get_funds(market=None, env=None):
    market = to_trd_market(market or get_default_market())
    env = to_trd_env(env or get_default_env())
    mkt = _market_str(market)
    currency = _market_currency(market)

    conn_mgr = get_connection_manager()
    ctx = conn_mgr.get_trade_context(market, env)
    acc_id = conn_mgr.get_acc_id(market, env)

    try:
        ret, funds_data = ctx.accinfo_query(
            trd_env=env, acc_id=acc_id, refresh_cache=True, currency=currency
        )
        if ret != RET_OK:
            return {"success": False, "error_msg": str(funds_data)}
        if funds_data is None or funds_data.empty:
            return {"success": False, "error_msg": "未获取到资金数据"}

        row = funds_data.iloc[0]
        if mkt == "HK":
            local_cash = safe_float(row.get("hk_cash"))
        else:
            local_cash = safe_float(row.get("us_cash"))
        cash = safe_float(row.get("cash"))
        if not local_cash:
            local_cash = cash

        funds = {
            "total_assets": safe_float(row.get("total_assets")),
            "market_val": safe_float(row.get("market_val")),
            "cash": cash,
            "local_cash": local_cash,
            "unrealized_pl": safe_float(row.get("unrealized_pl")),
            "realized_pl": safe_float(row.get("realized_pl")),
        }

        return {"success": True, "funds": funds}
    except Exception as e:
        logger.error(f"获取资金失败 [{mkt}]: {e}")
        return {"success": False, "error_msg": str(e)}


def get_positions_and_funds(market=None, env=None, include_zero=False):
    market = market or get_default_market()
    env = env or get_default_env()

    pos_result = get_positions(market=market, env=env, include_zero=include_zero)
    funds_result = get_funds(market=market, env=env)

    success = pos_result.get("success", False)

    result = {
        "success": success,
        "positions": pos_result.get("positions") if success else None,
        "today_pl_total": pos_result.get("today_pl_total", 0),
        "funds": funds_result.get("funds") if funds_result.get("success") else None,
    }

    if not success:
        result["error_msg"] = pos_result.get("error_msg", "获取持仓失败")

    return result
