"""本地 Skill 扫描器 —— 扫描 skills/ 目录,发现并管理 Hermes Skill。

Skill 目录结构:
    skills/
    └── <skill-name>/
        ├── manifest.yaml    # 必需: 元信息
        ├── run.py           # 可选: 执行入口
        └── prompt.md        # 可选: Prompt 模板

manifest.yaml 格式:
    name: my-skill
    display_name: 我的技能
    description: 技能描述
    version: 1.0.0
    author: xxx
    tags: [analysis, report]
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

DEFAULT_SKILLS_DIR = "skills"


@dataclass
class SkillManifest:
    """Skill 元信息"""
    name: str = ""
    display_name: str = ""
    description: str = ""
    version: str = "1.0.0"
    author: str = ""
    tags: list[str] = field(default_factory=list)
    enabled: bool = True

    # 路径信息
    dir_path: str = ""
    has_runner: bool = False     # 是否有 run.py
    has_prompt: bool = False     # 是否有 prompt.md

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "display_name": self.display_name,
            "description": self.description,
            "version": self.version,
            "author": self.author,
            "tags": self.tags,
            "enabled": self.enabled,
            "dir_path": self.dir_path,
            "has_runner": self.has_runner,
            "has_prompt": self.has_prompt,
        }


def scan_skills(base_dir: str | None = None) -> list[SkillManifest]:
    """扫描 skills/ 目录,返回所有发现的 Skill 清单。

    Args:
        base_dir: skills 目录路径,默认使用项目根下的 skills/

    Returns:
        SkillManifest 列表
    """
    if base_dir is None:
        # 尝试从项目根目录找
        candidates = [
            Path("skills"),
            Path(__file__).parent.parent.parent.parent / "skills",
        ]
        skills_dir = None
        for c in candidates:
            if c.is_dir():
                skills_dir = c
                break
        if skills_dir is None:
            return []
    else:
        skills_dir = Path(base_dir)

    if not skills_dir.is_dir():
        return []

    manifests: list[SkillManifest] = []
    for entry in sorted(skills_dir.iterdir()):
        if not entry.is_dir():
            continue
        manifest_file = entry / "manifest.yaml"
        if not manifest_file.is_file():
            continue

        try:
            with open(manifest_file, encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
        except Exception as e:
            logger.warning(f"读取 skill manifest 失败: {manifest_file}: {e}")
            continue

        manifests.append(SkillManifest(
            name=str(data.get("name", entry.name)),
            display_name=str(data.get("display_name", entry.name)),
            description=str(data.get("description", "")),
            version=str(data.get("version", "1.0.0")),
            author=str(data.get("author", "")),
            tags=list(data.get("tags", [])),
            enabled=bool(data.get("enabled", True)),
            dir_path=str(entry),
            has_runner=(entry / "run.py").is_file(),
            has_prompt=(entry / "prompt.md").is_file(),
        ))

    return manifests


def get_skill(skill_name: str, base_dir: str | None = None) -> SkillManifest | None:
    """获取单个 Skill 的详细信息。"""
    skills = scan_skills(base_dir)
    for s in skills:
        if s.name == skill_name:
            return s
    return None


def read_skill_prompt(skill_name: str, base_dir: str | None = None) -> str | None:
    """读取 Skill 的 prompt 模板。"""
    skill = get_skill(skill_name, base_dir)
    if skill is None:
        return None
    prompt_file = Path(skill.dir_path) / "prompt.md"
    if not prompt_file.is_file():
        return None
    try:
        return prompt_file.read_text(encoding="utf-8")
    except Exception as e:
        logger.warning(f"读取 prompt 失败: {prompt_file}: {e}")
        return None


def ensure_skills_dir(base_dir: str | None = None) -> Path:
    """确保 skills 目录存在。"""
    if base_dir:
        p = Path(base_dir)
    else:
        p = Path("skills")
    p.mkdir(parents=True, exist_ok=True)
    # 创建 .gitkeep 和示例 skill
    (p / ".gitkeep").touch(exist_ok=True)
    return p
