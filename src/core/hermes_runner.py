"""Hermes Skill 执行引擎 —— 运行本地 Skill 并收集输出。

支持的 Skill 类型:
1. Python runner: skills/<name>/run.py 中有 run(context) 函数
2. Prompt-only: 仅有 prompt.md,由 AI 代为执行(通过 MCP 或 Chat)
"""

from __future__ import annotations

import importlib.util
import logging
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.core.local_skill_scanner import (
    SkillManifest,
    get_skill,
    read_skill_prompt,
    scan_skills,
)

logger = logging.getLogger(__name__)


@dataclass
class SkillRunResult:
    """Skill 运行结果"""
    skill_name: str = ""
    success: bool = False
    output: str = ""
    error: str = ""
    duration_ms: float = 0.0
    started_at: str = ""
    finished_at: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "skill_name": self.skill_name,
            "success": self.success,
            "output": self.output,
            "error": self.error,
            "duration_ms": self.duration_ms,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "metadata": self.metadata,
        }


def run_skill(
    skill_name: str,
    params: dict[str, Any] | None = None,
    base_dir: str | None = None,
) -> SkillRunResult:
    """运行指定的 Skill。

    1. 加载 manifest
    2. 如果存在 run.py,动态导入并调用 run(context)
    3. 如果仅有 prompt.md,返回 prompt 内容(由调用方通过 AI 执行)
    4. 返回 SkillRunResult

    Args:
        skill_name: Skill 名称
        params: 传递给 run() 的参数
        base_dir: skills 目录路径

    Returns:
        SkillRunResult
    """
    import time
    start = time.monotonic()
    started_at = datetime.now(timezone.utc).isoformat()
    params = params or {}

    skill = get_skill(skill_name, base_dir)
    if skill is None:
        return SkillRunResult(
            skill_name=skill_name,
            success=False,
            error=f"Skill '{skill_name}' 未找到",
            started_at=started_at,
            finished_at=datetime.now(timezone.utc).isoformat(),
            duration_ms=(time.monotonic() - start) * 1000,
        )

    # 如果有 Python runner,执行它
    if skill.has_runner:
        try:
            runner_path = Path(skill.dir_path) / "run.py"
            # 动态加载模块
            spec = importlib.util.spec_from_file_location(
                f"skill_{skill_name}", str(runner_path)
            )
            if spec is None or spec.loader is None:
                raise ImportError(f"无法加载 skill runner: {runner_path}")

            module = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = module
            spec.loader.exec_module(module)

            if not hasattr(module, "run"):
                raise AttributeError("Skill runner 缺少 run(context) 函数")

            context = {
                "params": params,
                "skill_dir": skill.dir_path,
                "manifest": skill.to_dict(),
            }
            output = module.run(context)
        except Exception as e:
            logger.error(f"Skill '{skill_name}' 执行失败: {e}", exc_info=True)
            return SkillRunResult(
                skill_name=skill_name,
                success=False,
                error=str(e),
                started_at=started_at,
                finished_at=datetime.now(timezone.utc).isoformat(),
                duration_ms=(time.monotonic() - start) * 1000,
            )

        return SkillRunResult(
            skill_name=skill_name,
            success=True,
            output=str(output) if output else "",
            started_at=started_at,
            finished_at=datetime.now(timezone.utc).isoformat(),
            duration_ms=(time.monotonic() - start) * 1000,
            metadata={"runner_type": "python"},
        )

    # 如果仅有 prompt,返回 prompt
    if skill.has_prompt:
        prompt = read_skill_prompt(skill_name, base_dir)
        return SkillRunResult(
            skill_name=skill_name,
            success=True,
            output=prompt or "",
            started_at=started_at,
            finished_at=datetime.now(timezone.utc).isoformat(),
            duration_ms=(time.monotonic() - start) * 1000,
            metadata={"runner_type": "prompt_only"},
        )

    return SkillRunResult(
        skill_name=skill_name,
        success=False,
        error=f"Skill '{skill_name}' 无可执行 runner 或 prompt",
        started_at=started_at,
        finished_at=datetime.now(timezone.utc).isoformat(),
        duration_ms=(time.monotonic() - start) * 1000,
    )


def get_skill_report(
    skill_name: str,
    params: dict[str, Any] | None = None,
    base_dir: str | None = None,
) -> dict[str, Any]:
    """获取 Skill 执行报告(包含 manifest + 执行结果)。"""
    skill = get_skill(skill_name, base_dir)
    if skill is None:
        return {"error": f"Skill '{skill_name}' 未找到"}

    result = run_skill(skill_name, params, base_dir)

    return {
        "manifest": skill.to_dict(),
        "result": result.to_dict(),
    }


def run_all_skills(
    base_dir: str | None = None,
    filter_tags: list[str] | None = None,
) -> list[dict[str, Any]]:
    """运行所有已启用的 Skill。

    Args:
        base_dir: skills 目录
        filter_tags: 仅运行包含指定标签的 skill

    Returns:
        各 skill 的执行报告列表
    """
    skills = scan_skills(base_dir)
    reports = []
    for s in skills:
        if not s.enabled:
            continue
        if filter_tags and not any(t in s.tags for t in filter_tags):
            continue
        report = get_skill_report(s.name, base_dir=base_dir)
        reports.append(report)
    return reports
