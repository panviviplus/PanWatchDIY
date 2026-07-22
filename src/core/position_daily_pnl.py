"""持仓每日盈亏计算 —— 提供 Chat 上下文的持仓盈亏数据。

用于在聊天上下文中注入:
- 各持仓的当日盈亏和累计盈亏
- 整体组合当日/累计盈亏摘要
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta

from sqlalchemy.orm import Session

from src.web.models import Position, Stock

logger = logging.getLogger(__name__)

# 北京时间
_CN_TZ = timezone(timedelta(hours=8))


def _today_str() -> str:
    return datetime.now(_CN_TZ).strftime("%Y-%m-%d")


def get_position_pnl_summary(db: Session) -> str:
    """获取持仓盈亏摘要文本，供 Chat 上下文注入。

    返回人类可读的摘要，无持仓时返回空字符串。
    """
    positions = db.query(Position).filter(Position.quantity > 0).all()
    if not positions:
        return ""

    lines = ["## 当前持仓盈亏"]
    total_market_value = 0.0
    total_cost = 0.0

    for pos in positions:
        stock = db.query(Stock).filter(Stock.id == pos.stock_id).first()
        if not stock:
            continue
        qty = int(pos.quantity or 0)
        cost = float(pos.cost_price or 0)
        market_price = float(pos.current_price or cost)
        if qty <= 0 or cost <= 0:
            continue

        mv = market_price * qty
        cost_total = cost * qty
        pnl = mv - cost_total
        pnl_pct = (pnl / cost_total * 100) if cost_total > 0 else 0
        total_market_value += mv
        total_cost += cost_total

        emoji = "🟢" if pnl > 0 else ("🔴" if pnl < 0 else "⚪")
        lines.append(
            f"- {stock.name}({stock.symbol}) | "
            f"持仓{qty}股 | 成本¥{cost:.2f} | 现价¥{market_price:.2f} | "
            f"{emoji} {pnl:+.2f} ({pnl_pct:+.2f}%)"
        )

    if not lines[1:]:
        return ""

    total_pnl = total_market_value - total_cost
    total_pnl_pct = (total_pnl / total_cost * 100) if total_cost > 0 else 0
    emoji = "🟢" if total_pnl > 0 else ("🔴" if total_pnl < 0 else "⚪")
    lines.append(
        f"\n**合计**: 市值 ¥{total_market_value:,.2f} | "
        f"{emoji} 累计盈亏 {total_pnl:+,.2f} ({total_pnl_pct:+.2f}%)"
    )

    return "\n".join(lines)
