"""项目代码接口：扫描本地目录、维护关联、供简历改写使用。"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from job_scout.codebase import (
    browse_dir,
    delete_saved,
    discover_projects,
    get_context,
    list_saved,
    save_scan,
    scan_project,
)
from job_scout.rag.llm import get_llm

router = APIRouter(prefix="/code", tags=["code"])


class ScanRequest(BaseModel):
    # 本地目录绝对路径，比如 F:\project_work\AI_Chat
    path: str = Field(min_length=1, max_length=500)
    # 对应简历里的项目名，留空则用目录名
    project_name: str = Field(default="", max_length=100)


class ScanManyRequest(BaseModel):
    # 父目录，自动扫描其下所有子项目
    path: str = Field(min_length=1, max_length=500)
    # 只扫这些子目录名（留空则全扫）
    only: list[str] = Field(default_factory=list)


class ReviewRequest(BaseModel):
    # 简历里的项目名
    project: str = Field(min_length=1, max_length=100)


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
    """扫描一个本地项目并保存摘要。

    有模型 Key 时会读核心文件代码、让 LLM 写项目介绍（约 20 秒）；
    没有就退回规则版清单摘要。
    """
    result = scan_project(req.path)
    if not result.ok:
        raise HTTPException(400, result.error or "扫描失败")
    if result.file_count == 0:
        raise HTTPException(400, "这个目录里没找到源码文件（支持 py/ts/tsx/js/vue/java/go 等）")

    saved = save_scan(result, req.project_name, llm=get_llm())
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


# 注意：静态路径必须定义在 /{slug} 之前，否则 /code/browse 会被当成 slug 匹配走，
# 结果是 405 Method Not Allowed（只有 DELETE 注册过 /{slug}）。

@router.get("/context")
def context(project: str = "") -> dict:
    """预览改写时会用到的代码摘要。"""
    text = get_context(project) if project else ""
    return {"project": project, "chars": len(text), "summary": text}


@router.get("/browse")
def browse(path: str = "") -> dict:
    """列目录，供前端的文件夹选择器用。path 留空列出盘符。"""
    return browse_dir(path)


@router.get("/discover")
def discover(path: str) -> dict:
    """自动发现一个父目录下的一级子项目。"""
    return {"path": path, "items": discover_projects(path)}


@router.delete("/{slug}")
def remove(slug: str) -> dict:
    if not delete_saved(slug):
        raise HTTPException(404, "没找到这个项目")
    return {"ok": True}


@router.post("/review")
def review(req: ReviewRequest) -> dict:
    """对照项目代码审查简历里的该项目描述，指出不实、遗漏和改法。"""
    from job_scout.profile import load_profile, review_resume_vs_code
    from job_scout.rag.llm import get_llm

    profile = load_profile()
    if profile is None or not profile.has_content:
        raise HTTPException(400, "还没有上传简历，先到 /profile 上传 PDF")
    llm = get_llm()
    if llm is None:
        raise HTTPException(400, "没配置模型 Key，无法分析")

    ctx = get_context(req.project)
    if not ctx:
        raise HTTPException(400, f"「{req.project}」还没有关联代码，先在简历页添加项目")

    result = review_resume_vs_code(profile, req.project, ctx, llm)
    if result.get("error"):
        raise HTTPException(400, result["error"])
    return result


@router.post("/scan-many")
def scan_many(req: ScanManyRequest) -> dict:
    """批量扫描父目录下的子项目，一次全部关联。"""
    candidates = discover_projects(req.path)
    if req.only:
        keep = set(req.only)
        candidates = [c for c in candidates if c["name"] in keep]

    results: list[dict] = []
    llm = get_llm()
    for c in candidates:
        scan = scan_project(c["path"])
        if not scan.ok or scan.file_count == 0:
            results.append({"name": c["name"], "ok": False, "error": scan.error or "没找到源码"})
            continue
        saved = save_scan(scan, c["name"], llm=llm)
        results.append(
            {
                "name": saved["project_name"],
                "ok": True,
                "slug": saved["slug"],
                "file_count": saved["file_count"],
                "line_count": saved["line_count"],
            }
        )

    return {"total": len(results), "ok_count": sum(1 for r in results if r["ok"]), "items": results}
