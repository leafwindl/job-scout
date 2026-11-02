"""我的画像接口：上传简历 PDF、读取、手工编辑。"""

from __future__ import annotations

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel

from job_scout.profile import (
    Profile,
    extract_pdf_text,
    load_profile,
    parse_profile,
    save_profile,
    save_resume_pdf,
)
from job_scout.rag.llm import get_llm

router = APIRouter(prefix="/profile", tags=["profile"])


class ProfilePatch(BaseModel):
    name: str | None = None
    target: str | None = None
    skills: list[str] | None = None
    education: list[dict] | None = None
    projects: list[dict] | None = None
    experience: list[dict] | None = None


@router.get("")
def get_profile() -> dict:
    p = load_profile()
    if p is None:
        return {"uploaded": False}
    return {"uploaded": True, **p.to_dict()}


@router.post("/upload")
async def upload_resume(file: UploadFile = File(...)) -> dict:
    name = (file.filename or "resume.pdf").lower()
    if not name.endswith(".pdf"):
        raise HTTPException(400, "只支持 PDF（Word 请先另存为 PDF）")

    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(400, "文件超过 10MB")
    if not content:
        raise HTTPException(400, "空文件")

    path = save_resume_pdf(file.filename or "resume.pdf", content)

    try:
        text = extract_pdf_text(path)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(400, f"PDF 解析失败：{e}") from e

    if len(text.strip()) < 30:
        raise HTTPException(
            400, "没从 PDF 里提取到文字，可能是扫描件或图片版，请导出文字版 PDF"
        )

    llm = get_llm()
    profile = parse_profile(text, llm) if llm else Profile(raw_text=text)
    profile.source_file = path.name
    save_profile(profile)

    return {
        "ok": True,
        "source": path.name,
        "chars": len(text),
        "skills": len(profile.skills),
        "projects": len(profile.projects),
        "experience": len(profile.experience),
        "profile": profile.to_dict(),
    }


@router.patch("")
def patch_profile(patch: ProfilePatch) -> dict:
    p = load_profile()
    if p is None:
        p = Profile()

    for field_name in ("name", "target", "skills", "education", "projects", "experience"):
        value = getattr(patch, field_name)
        if value is not None:
            setattr(p, field_name, value)

    save_profile(p)
    return {"ok": True, **p.to_dict()}
