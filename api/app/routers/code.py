"""项目代码接口：扫描本地目录、维护关联、供简历改写使用。"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from job_scout.codebase import (
    delete_saved,
    get_context,
    list_saved,
    save_scan,
    scan_project,
)

router = APIRouter(prefix="/code", tags=["code"])


class ScanRequest(BaseModel):
    # 本地目录绝对路径，比如 F:\project_work\AI_Chat
    path: str = Field(min_length=1, max_length=500)
    # 对应简历里的项目名，留空则用目录名
    project_name: str = Field(default="", max_length=100)


class ScanResponse(BaseModel):
    project_name: str
    slug: str
    path: str
    file_count: int
    line_count: int
    langs: dict[str, int]
    deps: list[str]
    routes: list[str]
    summary: str


@router.post("/scan", response_model=ScanResponse)
def scan(req: ScanRequest) -> ScanResponse:
    """扫描一个本地项目并保存摘要。"""
    result = scan_project(req.path)
    if not result.ok:
        raise HTTPException(400, result.error or "扫描失败")
    if result.file_count == 0:
        raise HTTPException(400, "这个目录里没找到源码文件（支持 py/ts/tsx/js/vue/java/go 等）")

    saved = save_scan(result, req.project_name)
    return ScanResponse(
        project_name=saved["project_name"],
        slug=saved["slug"],
        path=saved["path"],
        file_count=saved["file_count"],
        line_count=saved["line_count"],
        langs=saved["langs"],
        deps=saved["deps"][:20],
        routes=saved["routes"][:20],
        summary=saved["summary"],
    )


@router.get("")
def items() -> dict:
    return {"items": list_saved()}


@router.delete("/{slug}")
def remove(slug: str) -> dict:
    if not delete_saved(slug):
        raise HTTPException(404, "没找到这个项目")
    return {"ok": True}


@router.get("/context")
def context(project: str = "") -> dict:
    """预览改写时会用到的代码摘要。"""
    text = get_context(project) if project else ""
    return {"project": project, "chars": len(text), "summary": text}
