"""股票新闻上下文 —— 为 Chat 注入相关新闻。

从数据库中获取指定股票的最新新闻，格式化为 Chat 上下文。
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

_CN_TZ = timezone(timedelta(hours=8))


def get_news_context(
    db: Session,
    stock_symbol: str | None = None,
    stock_name: str | None = None,
    hours: int = 24,
    limit: int = 10,
) -> str:
    """获取股票相关新闻，格式化为 Chat 上下文。

    尝试从数据库的 news 相关表获取。如果不存在 news 专用表，
    则返回空字符串（不阻断聊天流程）。

    Args:
        db: 数据库会话
        stock_symbol: 股票代码
        stock_name: 股票名称（用于文本搜索）
        hours: 回看时间
        limit: 最多返回条数

    Returns:
        人类可读的新闻上下文，无新闻时返回空字符串。
    """
    # 尝试从 StockNews 表获取（如果存在）
    news_items: list[dict] = []
    try:
        from src.web.models import StockNews  # noqa: F811
        query = db.query(StockNews).order_by(StockNews.published_at.desc())
        if stock_symbol:
            query = query.filter(StockNews.related_symbols.contains(stock_symbol))
        elif stock_name:
            query = query.filter(StockNews.title.contains(stock_name))
        rows = query.limit(limit).all()
        for r in rows:
            news_items.append({
                "title": getattr(r, "title", ""),
                "source": getattr(r, "source", ""),
                "published_at": getattr(r, "published_at", None),
                "url": getattr(r, "url", ""),
            })
    except Exception:
        pass  # StockNews 表可能不存在

    if not news_items:
        return ""

    lines = ["## 相关新闻"]
    for n in news_items:
        ts = ""
        if n.get("published_at"):
            pt = n["published_at"]
            if hasattr(pt, "strftime"):
                ts = pt.strftime("%m-%d %H:%M")
            else:
                ts = str(pt)[:16]
        source = n.get("source", "")
        title = n.get("title", "")
        lines.append(f"- [{ts}] ({source}) {title}")

    return "\n".join(lines)
