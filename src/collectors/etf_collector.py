"""场内 ETF 数据采集器 —— 基于东方财富 HTTP API。

数据口径:
- 实时行情+IOPV+折溢价+规模: 东财 push2 ETF 列表 API(全量一次,15min TTL 缓存)
- 成分股: 复用 fund_collector.fetch_fund_top_holdings(东财基金档案)
- 净值历史: 复用 fund_collector.fetch_fund_performance(东财基金净值)

设计要点:
- spot 是全量拉取(1000+ 只),进程级缓存,15min 内不重拉。
- 所有取数异常返回 None/空列表,不拖垮调用方。
- 无需 akshare 依赖,纯 httpx + 正则。
"""

from __future__ import annotations

import json
import logging
import re
import time
from datetime import datetime, timedelta
from typing import Any

import httpx

from src.collectors.fund_collector import (
    fetch_fund_top_holdings,
    fetch_fund_performance,
)

logger = logging.getLogger(__name__)

# 东财全量 ETF 列表 API
_ETF_SPOT_URL = "https://push2.eastmoney.com/api/qt/clist/get"
_ETF_SPOT_PARAMS = {
    "pn": "1",
    "pz": "2000",
    "po": "1",
    "np": "1",
    "ut": "bd1d9ddb04089700cf9c27f6f7426281",
    "fltt": "2",
    "invt": "2",
    "fid": "f3",
    "fs": "b:MK0021,b:MK0022,b:MK0023,b:MK0024",
    "fields": "f2,f3,f4,f12,f14,f15,f16,f17,f18,f20,f21",
    "_": "",
}
# f2=最新价, f3=涨跌幅, f4=涨跌额, f12=代码, f14=名称
# f15=最高, f16=最低, f17=今开, f18=昨收, f20=总市值(规模), f21=流通市值

# IOPV 单独 API (东财只对部分 ETF 提供)
_IOPV_URL = "https://push2.eastmoney.com/api/qt/stock/get"
_IOPV_PARAMS_BASE = {
    "ut": "bd1d9ddb04089700cf9c27f6f7426281",
    "fltt": "2",
    "invt": "2",
    "fields": "f43,f44,f45,f46,f48,f50,f51,f52,f57,f58,f60,f107,f116,f117,f161,f162,f167,f168,f169,f170,f171",
}

# 缓存
_SPOT_CACHE: list[dict] | None = None
_SPOT_CACHE_TS: float = 0.0
_SPOT_CACHE_TTL: float = 900.0  # 15min

_HOLDINGS_CACHE: dict[str, tuple[float, list[dict]]] = {}
_HOLDINGS_TTL: float = 3600.0  # 1h

_NAV_CACHE: dict[str, tuple[float, list[dict]]] = {}
_NAV_TTL: float = 3600.0  # 1h

_QUOTE_BATCH_CACHE: dict[str, tuple[float, dict]] = {}
_QUOTE_BATCH_TTL: float = 60.0  # 1min


def _safe_float(v: Any) -> float | None:
    """容错转 float。"""
    if v is None:
        return None
    try:
        f = float(v)
        if str(f) in ("nan", "inf", "-inf"):
            return None
        return f
    except (TypeError, ValueError):
        return None


def _fetch_spot_all() -> list[dict]:
    """拉取全量 ETF spot(带缓存)。失败返回空列表。"""
    global _SPOT_CACHE, _SPOT_CACHE_TS
    now = time.time()
    if _SPOT_CACHE is not None and (now - _SPOT_CACHE_TS) < _SPOT_CACHE_TTL:
        return _SPOT_CACHE

    params = dict(_ETF_SPOT_PARAMS)
    params["_"] = str(int(now * 1000))
    try:
        with httpx.Client() as client:
            resp = client.get(_ETF_SPOT_URL, params=params, timeout=20)
            data = resp.json()
    except Exception as e:
        logger.warning("ETF spot 全量拉取失败: %s", e)
        return _SPOT_CACHE or []

    rows = (data.get("data") or {}).get("diff") or []
    result = []
    for r in rows:
        result.append({
            "symbol": str(r.get("f12", "")),
            "name": str(r.get("f14", "")),
            "price": _safe_float(r.get("f2")),
            "change_pct": _safe_float(r.get("f3")),
            "change_amt": _safe_float(r.get("f4")),
            "high": _safe_float(r.get("f15")),
            "low": _safe_float(r.get("f16")),
            "open": _safe_float(r.get("f17")),
            "prev_close": _safe_float(r.get("f18")),
            "total_value": _safe_float(r.get("f20")),  # 基金规模(元)
            "circulation_value": _safe_float(r.get("f21")),
            "iopv": None,
            "premium_pct": None,
            "turnover": None,
            "turnover_rate": None,
            "volume": None,
        })

    _SPOT_CACHE = result
    _SPOT_CACHE_TS = now
    return result


def _fetch_etf_quote_detail(symbol: str) -> dict | None:
    """拉取单只 ETF 的 IOPV/成交额/换手率等详细数据(带短缓存)。"""
    now = time.time()
    cached = _QUOTE_BATCH_CACHE.get(symbol)
    if cached and (now - cached[0]) < _QUOTE_BATCH_TTL:
        return cached[1]

    secid = f"1.{symbol}" if symbol.startswith(("5", "6", "9")) else f"0.{symbol}"
    params = dict(_IOPV_PARAMS_BASE)
    params["secid"] = secid
    params["_"] = str(int(now * 1000))
    try:
        with httpx.Client() as client:
            resp = client.get(_IOPV_URL, params=params, timeout=10)
            d = resp.json().get("data") or {}
    except Exception:
        return None

    result = {
        "iopv": _safe_float(d.get("f161")),         # IOPV(实时估值)
        "premium_pct": _safe_float(d.get("f169")),   # 折溢价率
        "turnover": _safe_float(d.get("f57")),        # 成交额
        "turnover_rate": _safe_float(d.get("f168")),  # 换手率
        "volume": _safe_float(d.get("f167")),         # 成交量
        "total_value": _safe_float(d.get("f116")),    # 总市值
    }
    _QUOTE_BATCH_CACHE[symbol] = (now, result)
    return result


def get_etf_spot(symbol: str) -> dict | None:
    """取单只 ETF 实时行情(含 IOPV/折溢价/规模)。未命中返回 None。"""
    sym = (symbol or "").strip()
    if not sym:
        return None
    all_spot = _fetch_spot_all()
    base = None
    for s in all_spot:
        if s["symbol"] == sym:
            base = dict(s)
            break
    if base is None:
        return None

    # 补充 IOPV 等详情
    detail = _fetch_etf_quote_detail(sym)
    if detail:
        base.update(detail)
    return base


def get_etf_holdings(symbol: str, top: int = 30) -> list[dict]:
    """取 ETF 成分股(复用 fund_collector,取最近季报,按占净值降序)。"""
    sym = (symbol or "").strip()
    now = time.time()
    cached = _HOLDINGS_CACHE.get(sym)
    if cached and (now - cached[0]) < _HOLDINGS_TTL:
        return cached[1][:top]

    try:
        raw = fetch_fund_top_holdings(sym, topline=top)
    except Exception as e:
        logger.warning("ETF %s 成分股拉取失败: %s", sym, e)
        raw = []

    result = []
    for h in raw:
        result.append({
            "symbol": str(h.get("code", "")),
            "name": str(h.get("name", "")),
            "weight_pct": h.get("weight"),
            "change_pct": h.get("change_pct"),
        })

    _HOLDINGS_CACHE[sym] = (now, result)
    return result[:top]


def get_etf_nav_history(symbol: str, days: int = 180) -> list[dict]:
    """取净值历史(复用 fund_collector,按日期升序,附日增长率)。"""
    sym = (symbol or "").strip()
    now = time.time()
    cached = _NAV_CACHE.get(f"{sym}:{days}")
    if cached and (now - cached[0]) < _NAV_TTL:
        return cached[1]

    try:
        perf = fetch_fund_performance(sym)
    except Exception as e:
        logger.warning("ETF %s 净值历史拉取失败: %s", sym, e)
        return []

    points = perf.get("points") or []
    nav = []
    for i, p in enumerate(points):
        ret = p.get("return_pct")
        change_pct = None
        if i > 0 and ret is not None:
            prev_ret = points[i - 1].get("return_pct")
            if prev_ret is not None:
                # 由累计收益率反推日增长率
                change_pct = ((1 + ret / 100) / (1 + prev_ret / 100) - 1) * 100
                change_pct = round(change_pct, 4)
        ts = p.get("ts")
        date_str = ""
        if ts:
            try:
                date_str = datetime.fromtimestamp(ts / 1000).strftime("%Y-%m-%d")
            except Exception:
                date_str = str(ts)
        nav.append({
            "date": date_str,
            "unit_nav": p.get("value"),
            "cum_nav": None,
            "change_pct": change_pct,
        })

    _NAV_CACHE[f"{sym}:{days}"] = (now, nav)
    return nav


def get_etf_overview(symbol: str, top: int = 30, nav_days: int = 180) -> dict:
    """聚合 ETF 详情:spot + 成分股 + 净值历史。各部分独立兜底。"""
    return {
        "symbol": (symbol or "").strip(),
        "spot": get_etf_spot(symbol),
        "holdings": get_etf_holdings(symbol, top=top),
        "nav_history": get_etf_nav_history(symbol, days=nav_days),
    }
