"""持仓交易流水上下文 —— 为 Chat 提供最近的交易记录。

格式化 PositionTrade 表记录为 Chat 上下文文本。
"""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from src.web.models import PositionTrade

logger = logging.getLogger(__name__)


def get_recent_trades_context(
    db: Session,
    stock_symbol: str | None = None,
    limit: int = 10,
) -> str:
    """获取最近交易流水，格式化为 Chat 上下文。

    Args:
        db: 数据库会话
        stock_symbol: 可选，按股票代码过滤
        limit: 返回最近 N 条记录

    Returns:
        人类可读的交易流水文本，无记录时返回空字符串。
    """
    query = db.query(PositionTrade).order_by(PositionTrade.traded_at.desc())
    if stock_symbol:
        query = query.filter(PositionTrade.stock_symbol == stock_symbol)
    trades = query.limit(limit).all()

    if not trades:
        return ""

    lines = ["## 最近交易记录"]
    for t in trades:
        side_label = "买入" if t.side == "buy" else "卖出"
        emoji = "📈" if t.side == "buy" else "📉"
        ts = ""
        if t.traded_at:
            ts = t.traded_at.strftime("%m-%d %H:%M") if hasattr(t.traded_at, "strftime") else str(t.traded_at)
        lines.append(
            f"- {ts} {emoji} {side_label} {getattr(t, 'stock_symbol', '')} "
            f"¥{float(t.price or 0):.2f} × {int(t.quantity or 0)}股 = "
            f"¥{float(t.amount or 0):,.2f}"
        )
        if getattr(t, "note", ""):
            lines.append(f"  备注: {t.note}")

    return "\n".join(lines)
