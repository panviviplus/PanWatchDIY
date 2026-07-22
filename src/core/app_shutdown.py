"""优雅关闭工具 —— 用于 lifespan shutdown 阶段有序停止后台任务。"""

from __future__ import annotations

import asyncio
import logging
from functools import wraps

logger = logging.getLogger(__name__)

_shutting_down = False


def mark_shutting_down() -> None:
    """标记服务正在关闭，所有后台任务应尽快退出。"""
    global _shutting_down
    _shutting_down = True
    logger.info("app_shutdown: shutting_down flag set")


def is_shutting_down() -> bool:
    return _shutting_down


def reset_shutdown_state() -> None:
    """仅用于测试：重置关闭状态。"""
    global _shutting_down
    _shutting_down = False


def raise_if_shutting_down() -> None:
    """如果正在关闭，抛出 CancelledError 以中断当前协程。"""
    if _shutting_down:
        raise asyncio.CancelledError("app is shutting down")


def scheduler_job(func):
    """装饰器：包裹 scheduler job，在关闭期间静默退出（不记录错误日志）。"""

    @wraps(func)
    async def wrapper(*args, **kwargs):
        if _shutting_down:
            return
        try:
            return await func(*args, **kwargs)
        except asyncio.CancelledError:
            # 关闭期间被取消，静默退出
            pass
        except Exception:
            if _shutting_down:
                # 关闭期间的异常忽略
                pass
            else:
                raise

    return wrapper


def shutdown_async_scheduler(scheduler, name: str = "scheduler") -> None:
    """安全关闭 AsyncIOScheduler 实例。"""
    if scheduler is None:
        return
    try:
        if hasattr(scheduler, "running") and scheduler.running:
            scheduler.shutdown(wait=False)
            logger.info("app_shutdown: %s stopped", name)
    except Exception:
        logger.warning("app_shutdown: error stopping %s", name, exc_info=True)


def graceful_shutdown(
    *,
    agent_scheduler=None,
    price_alert_scheduler=None,
    paper_trading_scheduler=None,
    context_maintenance_scheduler=None,
) -> None:
    """统一优雅关闭入口 —— 在 FastAPI lifespan shutdown 阶段调用。"""
    mark_shutting_down()

    # 停止所有后台 scheduler（先停高频的，再停低频的）
    shutdown_async_scheduler(price_alert_scheduler, "price_alert_scheduler")
    shutdown_async_scheduler(paper_trading_scheduler, "paper_trading_scheduler")
    shutdown_async_scheduler(context_maintenance_scheduler, "context_maintenance_scheduler")
    shutdown_async_scheduler(agent_scheduler, "agent_scheduler")

    logger.info("app_shutdown: graceful shutdown complete")
