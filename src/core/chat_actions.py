"""聊天动作解析 —— 从 AI 响应中提取可执行的结构化动作。

定义的动作类型:
- create_alert: 创建价格提醒
- add_position: 建议加仓
- reduce_position: 建议减仓
- set_stop_loss: 设置止损
- set_target_price: 设置止盈
- watch: 添加关注

前端 ChatActionCard 组件根据 action type 渲染对应的交互卡片。
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

# 匹配 AI 响应中的动作标签块: <!--PANWATCH_ACTIONS-->...<!--/PANWATCH_ACTIONS-->
_ACTIONS_TAG_RE = re.compile(
    r"<!--PANWATCH_ACTIONS-->\s*([\s\S]*?)\s*<!--/PANWATCH_ACTIONS-->",
    re.IGNORECASE,
)

_VALID_ACTIONS = frozenset({
    "create_alert",
    "add_position",
    "reduce_position",
    "set_stop_loss",
    "set_target_price",
    "watch",
})


@dataclass
class ChatAction:
    """可执行的聊天动作。"""

    action: str  # create_alert | add_position | reduce_position | ...
    label: str   # 展示标签, 如 "设置止损 ¥138.50"
    params: dict[str, Any] = field(default_factory=dict)
    # 通用字段
    symbol: str = ""
    market: str = "CN"
    price: float | None = None
    reason: str = ""


def extract_actions(content: str) -> list[ChatAction]:
    """从 AI 响应中提取结构化动作块。

    支持的格式:
        <!--PANWATCH_ACTIONS-->
        [
          {"action": "create_alert", "symbol": "600519", "price": 1600, "label": "跌破1600提醒"},
          {"action": "add_position", "symbol": "600519", "reason": "MACD金叉"}
        ]
        <!--/PANWATCH_ACTIONS-->

    无效动作静默跳过。
    """
    if not content:
        return []

    m = _ACTIONS_TAG_RE.search(content)
    if not m:
        return []

    raw = m.group(1).strip()
    try:
        items = json.loads(raw)
    except json.JSONDecodeError:
        logger.debug("无法解析 chat actions JSON: %.100s", raw)
        return []

    if isinstance(items, dict):
        items = [items]
    if not isinstance(items, list):
        return []

    actions: list[ChatAction] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        action_name = (item.get("action") or "").strip().lower()
        if action_name not in _VALID_ACTIONS:
            continue
        try:
            actions.append(ChatAction(
                action=action_name,
                label=str(item.get("label") or _default_label(action_name)),
                params={k: v for k, v in item.items() if k not in ("action", "label")},
                symbol=str(item.get("symbol") or ""),
                market=str(item.get("market") or "CN"),
                price=_safe_float(item.get("price")),
                reason=str(item.get("reason") or ""),
            ))
        except Exception:
            logger.debug("跳过无效 action: %s", item, exc_info=True)

    return actions


def strip_actions_block(content: str) -> str:
    """去掉 action 标签块,返回干净的对话文本。"""
    if not content:
        return content
    return _ACTIONS_TAG_RE.sub("", content).strip()


def _default_label(action: str) -> str:
    return {
        "create_alert": "创建提醒",
        "add_position": "建议加仓",
        "reduce_position": "建议减仓",
        "set_stop_loss": "设置止损",
        "set_target_price": "设置止盈",
        "watch": "添加关注",
    }.get(action, action)


def _safe_float(v: Any) -> float | None:
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None
