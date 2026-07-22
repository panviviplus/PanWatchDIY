"""本地 Skill 广场 API。"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.web.database import get_db
from src.web.api.auth import get_current_user
from src.core.local_skill_scanner import scan_skills, get_skill, ensure_skills_dir
from src.core.hermes_runner import run_skill, get_skill_report, run_all_skills

logger = logging.getLogger(__name__)
router = APIRouter()


class RunSkillBody(BaseModel):
    params: dict = {}


@router.get("")
def list_skills(db: Session = Depends(get_db)):
    """列出所有已发现的本地 Skill。"""
    _ = db
    skills = scan_skills()
    return [s.to_dict() for s in skills]


@router.get("/{skill_name}")
def skill_detail(skill_name: str, db: Session = Depends(get_db)):
    """获取 Skill 详细信息。"""
    _ = db
    skill = get_skill(skill_name)
    if skill is None:
        raise HTTPException(404, f"Skill '{skill_name}' 未找到")
    return skill.to_dict()


@router.post("/{skill_name}/run")
def run_skill_endpoint(skill_name: str, body: RunSkillBody | None = None, db: Session = Depends(get_db)):
    """运行指定 Skill。"""
    _ = db
    params = body.params if body else {}
    result = run_skill(skill_name, params=params)
    return result.to_dict()


@router.get("/{skill_name}/report")
def skill_report(skill_name: str, db: Session = Depends(get_db)):
    """获取 Skill 完整报告(manifest + 执行结果)。"""
    _ = db
    report = get_skill_report(skill_name)
    if "error" in report:
        raise HTTPException(404, report["error"])
    return report


@router.post("/run-all")
def run_all_skills_endpoint(db: Session = Depends(get_db)):
    """运行所有已启用的 Skill。"""
    _ = db
    reports = run_all_skills()
    return {"skills": reports, "count": len(reports)}


@router.post("/init")
def init_skills_dir(db: Session = Depends(get_db)):
    """初始化 skills 目录。"""
    _ = db
    skill_dir = ensure_skills_dir()
    return {"path": str(skill_dir), "ok": True}
