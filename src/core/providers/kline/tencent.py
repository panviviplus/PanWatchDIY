"""腾讯分钟K线 + 分时数据提供方。

基于腾讯 HTTP API（非 marketdata 包），提供:
- 分钟K线 (1m/5m/15m/30m/60m)
- 当日分时数据（价格 + 均价 + 成交量）
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime

from src.collectors.market_http import fetch_source
from src.models.market import MarketCode

logger = logging.getLogger(__name__)

_TENCENT_MINUTE_URL = "http://ifzq.gtimg.cn/appstock/app/kline/mkline"
_TENCENT_MINUTE_URL_BACKUP = "http://web.ifzq.gtimg.cn/appstock/app/minute/query"


@dataclass
class MinuteBar:
    """分钟K线数据"""
    time: str       # "2024-01-15 09:35" 或 "09:35"
    open: float
    close: float
    high: float
    low: float
    volume: float


@dataclass
class IntradayPoint:
    """分时数据点"""
    time: str       # "09:30"
    price: float
    volume: float
    avg_price: float  # 均价


def _to_tencent_symbol(symbol: str, market: str) -> str:
    """将 PanWatch 格式转为腾讯格式 (sh600519 / sz000001 / hk00700 / usAAPL)。"""
    code = symbol.strip().upper()
    m = market.strip().upper()
    if m == "CN":
        # 上海: 6/68/9 开头; 深圳: 0/3 开头
        if re.match(r'^[689]', code):
            return f"sh{code}"
        return f"sz{code}"
    elif m == "HK":
        return f"hk{code}"
    elif m == "US":
        return f"us{code.replace('.', '').replace('-', '')}"
    return code


def _parse_minute_kline_response(text: str) -> list[MinuteBar]:
    """解析腾讯分钟K线 JSON 响应。

    格式: { code: 0, data: { "sh600519": { "m5": [...] } } }
    每条: [time, open, close, high, low, volume]
    """
    if not text:
        return []
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        logger.debug(f"腾讯分钟K线 JSON 解析失败: {text[:200]}")
        return []

    if not isinstance(data, dict):
        return []
    inner = data.get("data", {})
    if not isinstance(inner, dict):
        return []

    bars: list[MinuteBar] = []
    for symbol_data in inner.values():
        if not isinstance(symbol_data, dict):
            continue
        # 键名可能是 m5 / m15 / m30 / m60
        for key, rows in symbol_data.items():
            if not key.startswith("m") or not isinstance(rows, list):
                continue
            for row in rows:
                if not isinstance(row, list) or len(row) < 6:
                    continue
                try:
                    bars.append(MinuteBar(
                        time=str(row[0]),
                        open=float(row[1]),
                        close=float(row[2]),
                        high=float(row[3]),
                        low=float(row[4]),
                        volume=float(row[5]),
                    ))
                except (ValueError, TypeError):
                    continue
    return bars


def _parse_intraday_response(text: str) -> list[IntradayPoint]:
    """解析腾讯分时图 JSON 响应。

    格式包含分钟级价格 + 均价 + 成交量。
    """
    if not text:
        return []
    # 去掉可能的 JS 变量包裹: var min_data=...
    text = text.strip()
    if "=" in text and not text.startswith("{"):
        text = text.split("=", 1)[1].strip().rstrip(";")

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        logger.debug(f"腾讯分时 JSON 解析失败: {text[:200]}")
        return []

    if not isinstance(data, dict):
        return []

    inner = data.get("data", {})
    if not isinstance(inner, dict):
        return []

    points: list[IntradayPoint] = []
    for symbol_data in inner.values():
        if not isinstance(symbol_data, dict):
            continue
        # 分钟数据在 "data" 数组里
        minute_data = symbol_data.get("data", [])
        if not isinstance(minute_data, list):
            continue

        for row in minute_data:
            if not isinstance(row, list):
                continue
            try:
                if len(row) >= 3:
                    points.append(IntradayPoint(
                        time=str(row[0]),
                        price=float(row[1]),
                        volume=float(row[2]) if len(row) > 2 else 0.0,
                        avg_price=float(row[3]) if len(row) > 3 else float(row[1]),
                    ))
            except (ValueError, TypeError):
                continue
    return points


class TencentMinuteKlineProvider:
    """腾讯分钟K线与分时数据提供方。

    使用腾讯 HTTP 接口获取分钟级 K 线和当日分时数据。
    与 marketdata 包完全隔离，独立管理。
    """

    # 分钟间隔 → API 参数映射
    INTERVAL_MAP = {
        "1m": "m1",
        "5m": "m5",
        "15m": "m15",
        "30m": "m30",
        "60m": "m60",
    }

    def _normalize_interval(self, interval: str) -> str:
        """标准化间隔字符串。"""
        iv = (interval or "5m").strip().lower()
        if iv in self.INTERVAL_MAP:
            return self.INTERVAL_MAP[iv]
        if iv in ("1", "1min", "1m"):
            return "m1"
        if iv in ("5", "5min", "5m"):
            return "m5"
        if iv in ("15", "15min", "15m"):
            return "m15"
        if iv in ("30", "30min", "30m"):
            return "m30"
        if iv in ("60", "60min", "60m", "1h"):
            return "m60"
        return "m5"

    def get_minute_klines(
        self, symbol: str, market: str = "CN", interval: str = "5m", count: int = 240
    ) -> list[MinuteBar]:
        """获取分钟K线数据。

        Args:
            symbol: 股票代码
            market: 市场 (CN/HK/US)
            interval: K线间隔 (1m/5m/15m/30m/60m)
            count: 获取根数 (默认 240)

        Returns:
            MinuteBar 列表，按时间升序
        """
        tsym = _to_tencent_symbol(symbol, market)
        m_interval = self._normalize_interval(interval)

        # 腾讯分钟K线 API
        # param 格式: sh600519,m5,,240
        param = f"{tsym},{m_interval},,{int(count)}"
        try:
            text = fetch_source(
                _TENCENT_MINUTE_URL,
                params={"param": param, "_var": "min_data"},
                host_key="ifzq.gtimg.cn",
                timeout=10,
                retries=2,
                log_label="腾讯分钟K线",
                symbol=symbol,
            )
        except Exception as e:
            logger.warning(f"腾讯分钟K线请求失败 {symbol}: {e}")
            return []

        if not text:
            return []

        bars = _parse_minute_kline_response(text)
        bars.sort(key=lambda b: b.time)
        return bars

    def get_intraday(self, symbol: str, market: str = "CN") -> list[IntradayPoint]:
        """获取当日分时数据（分钟级价格 + 均价 + 成交量）。

        Args:
            symbol: 股票代码
            market: 市场 (CN/HK/US)

        Returns:
            IntradayPoint 列表，按时间升序
        """
        tsym = _to_tencent_symbol(symbol, market)

        # 尝试分钟查询接口
        try:
            text = fetch_source(
                _TENCENT_MINUTE_URL_BACKUP,
                params={"param": tsym, "_var": "min_data"},
                host_key="web.ifzq.gtimg.cn",
                timeout=10,
                retries=2,
                log_label="腾讯分时图",
                symbol=symbol,
            )
        except Exception as e:
            logger.warning(f"腾讯分时数据请求失败 {symbol}: {e}")
            return []

        if not text:
            return []

        points = _parse_intraday_response(text)
        points.sort(key=lambda p: p.time)
        return points
