"""长线持仓计划引擎 —— 核心/卫星仓架构 + 分批加仓 + 滚仓降本。

核心概念:
- 核心仓(core): 长期持有,不轻易卖出,占比 60-70%
- 卫星仓(satellite): 波段操作,灵活进出,占比 30-40%
- 滚仓降本: 利用波段差价降低核心仓持仓成本
- 分批加仓: 按价格区间分 3-5 批建仓,降低单点风险

计划存储为 JSON,可通过 API CRUD。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class LongTermPlan:
    """长线持仓计划"""

    id: str = ""  # 唯一标识,如 "plan_20260722_600519"
    symbol: str = ""
    name: str = ""
    market: str = "CN"
    created_at: str = ""
    updated_at: str = ""

    # 仓位分层
    core_pct: float = 0.65         # 核心仓占比
    satellite_pct: float = 0.35    # 卫星仓占比
    target_total_shares: int = 0   # 目标总股数
    current_core_shares: int = 0   # 当前核心仓股数
    current_satellite_shares: int = 0  # 当前卫星仓股数
    core_cost: float = 0.0         # 核心仓成本价
    satellite_cost: float = 0.0    # 卫星仓成本价

    # 分批加仓计划
    batch_plan: list[BatchEntry] = field(default_factory=list)
    # 滚仓记录
    rolling_records: list[RollingRecord] = field(default_factory=list)

    # 策略参数
    stop_loss_pct: float = -15.0   # 核心仓止损线(%)
    target_return_pct: float = 50.0  # 目标收益率(%)
    rolling_diff_pct: float = 5.0  # 滚仓差价阈值(%)

    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "symbol": self.symbol,
            "name": self.name,
            "market": self.market,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "core_pct": self.core_pct,
            "satellite_pct": self.satellite_pct,
            "target_total_shares": self.target_total_shares,
            "current_core_shares": self.current_core_shares,
            "current_satellite_shares": self.current_satellite_shares,
            "core_cost": self.core_cost,
            "satellite_cost": self.satellite_cost,
            "batch_plan": [b.to_dict() for b in self.batch_plan],
            "rolling_records": [r.to_dict() for r in self.rolling_records],
            "stop_loss_pct": self.stop_loss_pct,
            "target_return_pct": self.target_return_pct,
            "rolling_diff_pct": self.rolling_diff_pct,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> LongTermPlan:
        return cls(
            id=str(d.get("id", "")),
            symbol=str(d.get("symbol", "")),
            name=str(d.get("name", "")),
            market=str(d.get("market", "CN")),
            created_at=str(d.get("created_at", "")),
            updated_at=str(d.get("updated_at", "")),
            core_pct=float(d.get("core_pct", 0.65)),
            satellite_pct=float(d.get("satellite_pct", 0.35)),
            target_total_shares=int(d.get("target_total_shares", 0)),
            current_core_shares=int(d.get("current_core_shares", 0)),
            current_satellite_shares=int(d.get("current_satellite_shares", 0)),
            core_cost=float(d.get("core_cost", 0)),
            satellite_cost=float(d.get("satellite_cost", 0)),
            batch_plan=[BatchEntry.from_dict(b) for b in d.get("batch_plan", [])],
            rolling_records=[RollingRecord.from_dict(r) for r in d.get("rolling_records", [])],
            stop_loss_pct=float(d.get("stop_loss_pct", -15)),
            target_return_pct=float(d.get("target_return_pct", 50)),
            rolling_diff_pct=float(d.get("rolling_diff_pct", 5)),
            notes=str(d.get("notes", "")),
        )


@dataclass
class BatchEntry:
    """分批加仓条目"""
    batch: int = 1          # 第几批
    price: float = 0.0      # 目标价格
    shares: int = 0         # 该批股数
    filled: bool = False    # 是否已成交
    filled_price: float | None = None
    filled_at: str | None = None  # 成交时间
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "batch": self.batch,
            "price": self.price,
            "shares": self.shares,
            "filled": self.filled,
            "filled_price": self.filled_price,
            "filled_at": self.filled_at,
            "note": self.note,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> BatchEntry:
        return cls(
            batch=int(d.get("batch", 1)),
            price=float(d.get("price", 0)),
            shares=int(d.get("shares", 0)),
            filled=bool(d.get("filled", False)),
            filled_price=d.get("filled_price"),
            filled_at=d.get("filled_at"),
            note=str(d.get("note", "")),
        )


@dataclass
class RollingRecord:
    """滚仓降本记录"""
    date: str = ""
    sell_price: float = 0.0
    sell_shares: int = 0
    buy_back_price: float = 0.0
    buy_back_shares: int = 0
    cost_reduction: float = 0.0  # 成本降低额
    new_cost: float = 0.0        # 滚仓后成本
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "date": self.date,
            "sell_price": self.sell_price,
            "sell_shares": self.sell_shares,
            "buy_back_price": self.buy_back_price,
            "buy_back_shares": self.buy_back_shares,
            "cost_reduction": self.cost_reduction,
            "new_cost": self.new_cost,
            "note": self.note,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> RollingRecord:
        return cls(
            date=str(d.get("date", "")),
            sell_price=float(d.get("sell_price", 0)),
            sell_shares=int(d.get("sell_shares", 0)),
            buy_back_price=float(d.get("buy_back_price", 0)),
            buy_back_shares=int(d.get("buy_back_shares", 0)),
            cost_reduction=float(d.get("cost_reduction", 0)),
            new_cost=float(d.get("new_cost", 0)),
            note=str(d.get("note", "")),
        )


def generate_batch_plan(
    current_price: float,
    target_shares: int,
    batches: int = 4,
    price_range_pct: float = 15.0,
) -> list[BatchEntry]:
    """自动生成分批加仓计划。

    在 [current_price, current_price * (1 - price_range_pct/100)] 区间内
    等分价格区间,均分目标股数。

    Args:
        current_price: 当前价格
        target_shares: 目标总股数
        batches: 分批次数
        price_range_pct: 价格区间百分比(正数,如 15 表示在现价下方 15% 区间)
    """
    if batches < 1 or target_shares <= 0 or current_price <= 0:
        return []

    low = current_price * (1 - price_range_pct / 100)
    high = current_price
    shares_per_batch = target_shares // batches
    remainder = target_shares % batches

    result = []
    for i in range(batches):
        ratio = (i + 1) / batches
        price = round(high - (high - low) * ratio, 2)
        shares = shares_per_batch + (1 if i < remainder else 0)
        result.append(BatchEntry(
            batch=i + 1,
            price=price,
            shares=shares,
            note=f"第{i+1}批: ¥{price:.2f} × {shares}股",
        ))
    return result


def calculate_rolling_cost_reduction(
    current_cost: float,
    sell_price: float,
    sell_shares: int,
    buy_back_price: float,
    buy_back_shares: int,
) -> float:
    """计算滚仓降本效果。

    sell_shares 股在 sell_price 卖出,buy_back_shares 股在 buy_back_price 买回,
    差价部分降低剩余持仓成本。
    """
    if sell_shares <= 0 or buy_back_shares <= 0:
        return current_cost
    profit = (sell_price - buy_back_price) * min(sell_shares, buy_back_shares)
    remaining = max(0, sell_shares - buy_back_shares)  # 净减仓股数
    if remaining > 0:
        # 有净减仓:利润分摊到剩余持仓
        new_cost = current_cost - profit / (current_cost > 0 and 1 or 1)  # simplified
        return round(new_cost, 4)
    return round(current_cost, 4)
