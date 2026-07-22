"""缠论情绪博弈策略 —— 基于缠论分型+均线系统的情绪博弈信号。

核心逻辑:
1. 分型识别: 顶分型/底分型判断趋势转折
2. 均线系统: MA5/MA10/MA20/MA60 多空排列
3. 情绪指标: 结合成交量、MACD 背离判断市场情绪
4. 博弈信号: 在关键分型位置给出买入/卖出/观望信号

信号输出:
- bullish_divergence: 底背离,看涨
- bearish_divergence: 顶背离,看跌
- consolidation: 中枢震荡,观望
- third_buy_point: 三买(回调不破中枢上沿)
- third_sell_point: 三卖(反弹不破中枢下沿)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ChanSignal:
    """缠论情绪信号"""

    symbol: str = ""
    name: str = ""
    market: str = "CN"
    signal_type: str = ""  # bullish_divergence / bearish_divergence / consolidation / third_buy / third_sell
    direction: str = ""  # long / short / neutral
    confidence: float = 0.0  # 0-100 信号强度
    price: float = 0.0
    description: str = ""
    generated_at: str = ""

    # 技术细节
    ma_alignment: str = ""  # bull排列 / bear排列 / 缠绕
    divergence_type: str = ""  # macd / volume / both
    pivot_high: float | None = None  # 最近顶分型
    pivot_low: float | None = None   # 最近底分型

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "name": self.name,
            "market": self.market,
            "signal_type": self.signal_type,
            "direction": self.direction,
            "confidence": self.confidence,
            "price": self.price,
            "description": self.description,
            "generated_at": self.generated_at,
            "ma_alignment": self.ma_alignment,
            "divergence_type": self.divergence_type,
            "pivot_high": self.pivot_high,
            "pivot_low": self.pivot_low,
        }


def detect_ma_alignment(prices: list[float]) -> str:
    """检测均线排列状态。

    简化实现:基于近5/10/20日均线判断。
    实际使用时需传入完整K线数据计算各周期MA。

    Returns:
        "bull" / "bear" / "tangle"
    """
    if len(prices) < 20:
        return "tangle"

    ma5 = sum(prices[-5:]) / 5
    ma10 = sum(prices[-10:]) / 10
    ma20 = sum(prices[-20:]) / 20

    if ma5 > ma10 > ma20:
        return "bull"
    elif ma5 < ma10 < ma20:
        return "bear"
    else:
        return "tangle"


def detect_pivot(prices: list[float], highs: list[float], lows: list[float]) -> dict:
    """检测最近的顶分型和底分型。

    分型定义(5根K线):
    - 顶分型: 中间K线最高价 > 左右各2根的最高价
    - 底分型: 中间K线最低价 < 左右各2根的最低价

    Returns:
        {"pivot_high": float|None, "pivot_low": float|None}
    """
    result: dict[str, float | None] = {"pivot_high": None, "pivot_low": None}

    if len(highs) < 5 or len(lows) < 5:
        return result

    # 遍历最近20根K线找分型
    window = min(20, len(highs))
    for i in range(2, window - 2):
        idx = len(highs) - window + i

        # 顶分型检测
        if highs[idx] > max(highs[idx-2], highs[idx-1], highs[idx+1], highs[idx+2]):
            result["pivot_high"] = highs[idx]

        # 底分型检测
        if lows[idx] < min(lows[idx-2], lows[idx-1], lows[idx+1], lows[idx+2]):
            result["pivot_low"] = lows[idx]

    return result


def analyze_chan_emotion(
    symbol: str,
    name: str,
    market: str,
    prices: list[float],
    highs: list[float],
    lows: list[float],
    volumes: list[float],
    current_price: float,
) -> ChanSignal | None:
    """执行缠论情绪分析。

    Args:
        symbol: 股票代码
        name: 股票名称
        market: 市场
        prices: 收盘价序列(最新在最后)
        highs: 最高价序列
        lows: 最低价序列
        volumes: 成交量序列
        current_price: 当前价格

    Returns:
        ChanSignal 或 None(数据不足)
    """
    if len(prices) < 30:
        return None

    ma_align = detect_ma_alignment(prices)
    pivots = detect_pivot(prices, highs, lows)

    # 简化情绪判断
    signal_type = "consolidation"
    direction = "neutral"
    confidence = 50.0
    description = "中枢震荡，等待方向选择"

    close_recent = prices[-1]
    close_prev = prices[-10]

    # 判断趋势
    if close_recent > close_prev and ma_align == "bull":
        if pivots["pivot_low"] is not None and close_recent > pivots["pivot_low"] * 1.02:
            signal_type = "third_buy"
            direction = "long"
            confidence = 70.0
            description = f"均线多头排列+回踩确认底分型{pivots['pivot_low']:.2f},三买信号"
    elif close_recent < close_prev and ma_align == "bear":
        if pivots["pivot_high"] is not None and close_recent < pivots["pivot_high"] * 0.98:
            signal_type = "third_sell"
            direction = "short"
            confidence = 70.0
            description = f"均线空头排列+反弹受阻顶分型{pivots['pivot_high']:.2f},三卖信号"

    # 量价背离检测(简化)
    if len(volumes) >= 5 and len(prices) >= 5:
        vol_trend = sum(volumes[-3:]) > sum(volumes[-5:-2])
        price_trend = close_recent > prices[-5]
        if price_trend and not vol_trend:
            divergence_type = "volume"
            if direction == "long":
                signal_type = "bearish_divergence"
                confidence = 65.0
                description = "价涨量缩,顶背离风险"

    return ChanSignal(
        symbol=symbol,
        name=name,
        market=market,
        signal_type=signal_type,
        direction=direction,
        confidence=round(confidence, 1),
        price=current_price,
        description=description,
        generated_at=datetime.now(timezone.utc).isoformat(),
        ma_alignment=ma_align,
        divergence_type="volume" if "背离" in description else "",
        pivot_high=pivots.get("pivot_high"),
        pivot_low=pivots.get("pivot_low"),
    )


def chan_signal_to_strategy_signal(
    chan: ChanSignal,
) -> dict[str, Any]:
    """将缠论信号转换为策略引擎可用的信号格式。"""
    action_map = {
        "third_buy": "buy",
        "bullish_divergence": "buy",
        "third_sell": "sell",
        "bearish_divergence": "sell",
        "consolidation": "hold",
    }
    return {
        "symbol": chan.symbol,
        "action": action_map.get(chan.signal_type, "hold"),
        "rank_score": chan.confidence,
        "strategy": "chan_emotion",
        "signal_detail": chan.description,
        "price": chan.price,
    }
