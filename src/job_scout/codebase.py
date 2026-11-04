"""扫描本地项目，生成「代码摘要」供简历改写使用。

为什么不用 LLM 读全量代码：一个项目几万行，成本和延迟都不划算。
先用规则抽取结构与依赖（可靠、毫秒级），再让 LLM 基于摘要润色措辞。

扫描内容：
- 语言分布（按行数）
- 依赖清单（package.json / pyproject.toml / requirements.txt / go.mod）
- 文件树（限制条数，只保留源码目录）
- 每个源文件的类名/函数名
- README 摘要

输出是一段结构化的 markdown，直接拼进改写 prompt。
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

# 扫描时直接跳过的目录
SKIP_DIRS = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    ".next",
    "dist",
    "build",
    ".pytest_cache",
    ".ruff_cache",
    "data",
    "logs",
    "coverage",
    ".idea",
    ".vscode",
    "target",
    "vendor",
    # Playwright 的浏览器配置目录里全是扩展缓存，不是项目代码
    ".playwright",
    "site-packages",
    ".turbo",
    ".cache",
}

# 视为源码的扩展名
CODE_EXT = {
    ".py": "Python",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".vue": "Vue",
    ".java": "Java",
    ".go": "Go",
    ".rs": "Rust",
    ".c": "C",
    ".cpp": "C++",
    ".h": "C/C++",
    ".cs": "C#",
    ".rb": "Ruby",
    ".php": "PHP",
    ".kt": "Kotlin",
    ".swift": "Swift",
    ".sql": "SQL",
    ".sh": "Shell",
    ".ps1": "PowerShell",
}

# 依赖文件
DEP_FILES = (
    "requirements.txt",
    "pyproject.toml",
    "package.json",
    "go.mod",
    "Cargo.toml",
    "pom.xml",
    "build.gradle",
)

# 单文件读取上限（避免读到大文件卡住）
MAX_FILE_BYTES = 200_000

# 每个文件最多记几个符号
MAX_SYMBOLS = 8

_CLASS_RE = re.compile(r"^\s*(?:export\s+)?(?:default\s+)?class\s+([A-Za-z_]\w+)", re.M)
_FUNC_RE = re.compile(
    r"^\s*(?:export\s+)?(?:async\s+)?(?:def|function|func|fn)\s+([A-Za-z_]\w+)", re.M
)
_TS_FUNC_RE = re.compile(
    r"^\s*(?:export\s+)?(?:const|let)\s+([A-Za-z_]\w+)\s*=\s*(?:async\s*)?\(", re.M
)
_ROUTE_RE = re.compile(r'@(?:router|app)\.(?:get|post|put|delete|patch)\(\s*["\']([^"\']+)', re.M)
_VUE_RE = re.compile(r"^\s*(?:export\s+default|export\s+const)\s+([A-Za-z_]\w+)", re.M)


@dataclass
class ProjectScan:
    """一次项目扫描的结果。"""

    path: str = ""
    name: str = ""
    file_count: int = 0
    line_count: int = 0
    langs: dict[str, int] = field(default_factory=dict)
    deps: list[str] = field(default_factory=list)
    tree: list[str] = field(default_factory=list)
    symbols: dict[str, list[str]] = field(default_factory=dict)
    routes: list[str] = field(default_factory=list)
    readme: str = ""
    ok: bool = True
    error: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    def summary_markdown(self, max_chars: int = 4000, display_name: str = "") -> str:
        """生成给 LLM 看的结构化摘要。

        display_name 用于显示简历里的项目名（而不是目录名），
        这样模型看到的是「Echo AI 助手 App」，不是「AI_Chat」。
        """
        if not self.ok:
            return ""

        name = display_name or self.name
        lines: list[str] = [f"项目名：{name}", f"路径：{self.path}"]

        if self.langs:
            top = sorted(self.langs.items(), key=lambda x: -x[1])[:4]
            lang_str = "、".join(f"{k} {v} 行" for k, v in top)
            lines.append(f"规模：{self.file_count} 个源文件，约 {self.line_count} 行（{lang_str}）")

        if self.deps:
            lines.append("依赖/技术栈：" + "、".join(self.deps[:30]))

        if self.routes:
            lines.append("对外接口：" + "、".join(self.routes[:15]))

        if self.tree:
            lines.append("目录结构：")
            lines.extend(f"  {t}" for t in self.tree[:45])

        if self.symbols:
            lines.append("主要模块与符号：")
            for f, syms in list(self.symbols.items())[:22]:
                lines.append(f"  {f}: {', '.join(syms)}")

        if self.readme:
            lines.append("README 摘录：")
            lines.append(self.readme)

        text = "\n".join(lines)
        return text[:max_chars]


def _read_text(p: Path, limit: int = MAX_FILE_BYTES) -> str:
    try:
        if p.stat().st_size > limit:
            return ""
        return p.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def _iter_files(root: Path, max_files: int = 4000):
    """遍历源文件，跳过无关目录和压缩产物。

    用 os.walk 而不是 rglob：rglob 会先把 node_modules 之类的几万个文件
    全部遍历一遍再过滤，在 Docker 挂载盘上能慢到超时。
    os.walk 可以就地剪枝，根本不进无关目录。
    """
    import os

    seen = 0
    for dirpath, dirnames, filenames in os.walk(root):
        # 就地剪枝
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]

        for name in filenames:
            if seen >= max_files:
                return
            low = name.lower()
            # 压缩后的库文件会把行数撑爆，对理解项目也没帮助
            if ".min." in low or low.endswith((".map", ".lock", ".svg", ".bundle.js")):
                continue
            p = Path(dirpath) / name
            if p.suffix.lower() not in CODE_EXT and name not in DEP_FILES:
                continue
            seen += 1
            yield p


def _extract_deps(root: Path) -> list[str]:
    """从依赖清单里抽技术栈。"""
    out: list[str] = []

    pkg = root / "package.json"
    if pkg.exists():
        try:
            data = json.loads(_read_text(pkg) or "{}")
            for key in ("dependencies", "devDependencies"):
                out.extend(data.get(key, {}).keys())
        except json.JSONDecodeError:
            pass

    req = root / "requirements.txt"
    if req.exists():
        for line in _read_text(req).splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            name = re.split(r"[<>=!~\[]", line, maxsplit=1)[0].strip()
            if name:
                out.append(name)

    toml = root / "pyproject.toml"
    if toml.exists():
        text = _read_text(toml)
        # 只从 dependencies / optional-dependencies 段里取，避免把 name、version 当依赖
        for block in re.finditer(
            r"(?:dependencies|optional-dependencies)\s*=\s*\[(.*?)\]", text, re.S
        ):
            for m in re.finditer(r'["\']([A-Za-z][\w.-]*)', block.group(1)):
                out.append(m.group(1))

    # 去重保序
    seen: set[str] = set()
    uniq = []
    for d in out:
        k = d.lower()
        if k not in seen:
            seen.add(k)
            uniq.append(d)
    return uniq


def _extract_symbols(text: str, suffix: str) -> list[str]:
    """从源码里抽类名/函数名/路由。"""
    if not text:
        return []
    found: list[str] = []
    for pat in (_CLASS_RE, _FUNC_RE):
        found.extend(pat.findall(text))
    if suffix in {".ts", ".tsx", ".js", ".jsx", ".vue"}:
        found.extend(_TS_FUNC_RE.findall(text))
    # 去重保序
    seen: set[str] = set()
    out = []
    for f in found:
        if f not in seen and len(f) > 2:
            seen.add(f)
            out.append(f)
    return out[:MAX_SYMBOLS]


def resolve_host_path(path: str) -> str:
    """把宿主机的 Windows 路径映射到容器内的挂载点。

    docker-compose 把 F:/ 只读挂到 /host/f，所以：
      F:\\project_work\\AI_Chat  ->  /host/f/project_work/AI_Chat

    本地跑（非容器）时直接返回原路径。
    """
    m = re.match(r"^([A-Za-z]):[\\/](.*)$", path.strip())
    if not m:
        return path
    drive, rest = m.group(1).lower(), m.group(2).replace("\\", "/")
    mapped = Path(f"/host/{drive}/{rest}")
    if mapped.exists():
        return str(mapped)
    return path


def scan_project(path: str | Path) -> ProjectScan:
    """扫描一个本地项目目录。"""
    raw = str(path)
    resolved = resolve_host_path(raw)
    root = Path(resolved).expanduser()
    if not root.exists():
        return ProjectScan(path=str(path), ok=False, error="路径不存在")
    if not root.is_dir():
        return ProjectScan(path=str(path), ok=False, error="不是目录")

    root = root.resolve()
    scan = ProjectScan(path=str(root), name=root.name)
    tree: list[str] = []

    for p in _iter_files(root):
        rel = p.relative_to(root)
        text = ""
        if p.suffix.lower() in CODE_EXT:
            scan.file_count += 1
            text = _read_text(p)
            n = text.count("\n") + 1
            scan.line_count += n
            lang = CODE_EXT[p.suffix.lower()]
            scan.langs[lang] = scan.langs.get(lang, 0) + n

            syms = _extract_symbols(text, p.suffix.lower())
            if syms:
                scan.symbols[str(rel).replace("\\", "/")] = syms
            if p.suffix == ".py":
                scan.routes.extend(_ROUTE_RE.findall(text))

            if len(tree) < 60:
                tree.append(str(rel).replace("\\", "/"))

    scan.tree = tree
    scan.deps = _extract_deps(root)
    scan.routes = list(dict.fromkeys(scan.routes))

    readme = root / "README.md"
    if readme.exists():
        scan.readme = _read_text(readme, 60_000)[:1200]

    return scan


# ==================== 目录浏览与项目发现 ====================

# 判定「这是一个项目」的标志文件
PROJECT_MARKERS = (
    "package.json",
    "pyproject.toml",
    "requirements.txt",
    "go.mod",
    "Cargo.toml",
    "pom.xml",
    "build.gradle",
    "settings.gradle",
    ".git",
    "README.md",
)

# 浏览目录时不过滤（用户可能想进任何目录），只挡住系统目录
BROWSE_SKIP = {".git", "node_modules", ".venv", "venv", "__pycache__", "System Volume Information"}


def browse_dir(path: str = "") -> dict:
    """列出一个目录下的子目录，供前端做文件夹选择器。

    path 为空时回到默认起点（Windows 下是各盘符根目录）。
    """
    if not path:
        # 列盘符
        # 只列**真正能访问**的盘符。
        # 容器里 docker-compose 只挂了 F: 到 /host/f，所以这里从 /host 实际读；
        # 直接把 C:/D:/E: 都列出来会让用户点了没反应（容器里那些路径不存在）。
        host_root = Path("/host")
        drives: list[dict] = []
        if host_root.exists():
            try:
                for child in sorted(host_root.iterdir()):
                    if child.is_dir():
                        letter = child.name.upper()
                        drives.append(
                            {
                                "name": f"{letter}:",
                                "path": f"{letter}:\\",
                                "is_project": False,
                            }
                        )
            except OSError:
                pass
        else:
            # 本地直接跑（非容器）时，列真实的 Windows 盘符
            for letter in "CDEFGHIJKLMNOPQRSTUVWXYZ":
                try:
                    if Path(f"{letter}:/").exists():
                        drives.append(
                            {
                                "name": f"{letter}:",
                                "path": f"{letter}:\\",
                                "is_project": False,
                            }
                        )
                except OSError:
                    continue

        return {
            "path": "",
            "parent": None,
            "dirs": drives,
            "at_root": True,
            # 只挂了一个盘时提示一下，免得用户以为别的地方还有
            "note": (
                f"只能访问已挂载的盘：{'、'.join(d['name'] for d in drives)}"
                "（要加别的盘，改 docker-compose.yml 的 volumes）"
                if drives
                else "容器里没有挂载任何宿主目录，检查 docker-compose.yml 的 volumes"
            ),
        }

    resolved = resolve_host_path(path)
    root = Path(resolved).expanduser()
    if not root.exists() or not root.is_dir():
        return {"path": path, "parent": None, "dirs": [], "error": "目录不存在"}

    dirs: list[dict] = []
    try:
        for child in sorted(root.iterdir(), key=lambda p: p.name.lower()):
            try:
                if not child.is_dir():
                    continue
            except OSError:
                continue
            if child.name in BROWSE_SKIP or child.name.startswith("."):
                continue
            is_project = any((child / m).exists() for m in PROJECT_MARKERS)
            dirs.append(
                {
                    "name": child.name,
                    # 回显成用户能看懂的宿主路径
                    "path": _to_host_path(child),
                    "is_project": is_project,
                }
            )
    except PermissionError:
        return {"path": path, "parent": None, "dirs": [], "error": "没有权限访问"}

    parent = _to_host_path(root.parent) if root.parent != root else None
    return {"path": _to_host_path(root), "parent": parent, "dirs": dirs, "at_root": False}


def _to_host_path(p: Path) -> str:
    """容器内 /host/f/x 转回 F:\\x，方便前端显示和回传。"""
    s = str(p).replace("\\", "/")
    m = re.match(r"^/host/([a-z])/(.*)$", s)
    if m:
        drive = m.group(1).upper()
        rest = m.group(2).replace("/", "\\")
        return f"{drive}:\\{rest}" if rest else f"{drive}:\\"
    return str(p)


def discover_projects(parent: str) -> list[dict]:
    """在一个父目录下自动发现一级子项目。

    判定标准：子目录里有 package.json / pyproject.toml / .git 等标志文件，
    或者子目录本身有 3 个以上源码文件。
    """
    resolved = resolve_host_path(parent)
    root = Path(resolved).expanduser()
    if not root.exists() or not root.is_dir():
        return []

    found: list[dict] = []
    try:
        children = sorted(root.iterdir(), key=lambda p: p.name.lower())
    except PermissionError:
        return []

    for child in children:
        try:
            if not child.is_dir() or child.name in BROWSE_SKIP or child.name.startswith("."):
                continue
        except OSError:
            continue

        markers = [m for m in PROJECT_MARKERS if (child / m).exists()]
        # 没标志文件时，数一下源码文件（只看前两层，别太重）
        code_files = 0
        if not markers:
            for p in child.iterdir():
                if p.is_file() and p.suffix.lower() in CODE_EXT:
                    code_files += 1
                    if code_files >= 3:
                        break

        if markers or code_files >= 3:
            found.append(
                {
                    "name": child.name,
                    "path": _to_host_path(child),
                    "markers": markers[:5],
                    "code_files": code_files,
                }
            )

    return found


# ==================== 存储 ====================

CODE_DIR = Path("data/code")


def _slug(name: str) -> str:
    """把项目名变成安全的文件名。"""
    s = re.sub(r"[^\w\u4e00-\u9fff-]+", "-", name.strip()).strip("-")
    return s or "project"


def _path_key(p: str) -> str:
    """路径归一化，用来判断「是不是同一个目录」。"""
    return (p or "").rstrip("\\/").replace("\\", "/").lower()


def save_scan(scan: ProjectScan, project_name: str = "") -> dict:
    """保存一次扫描结果。

    project_name 是简历里的项目名，用来建立关联（改写时按它找代码摘要）。

    同一个目录只保留一条：之前可能用目录名存过（AI_Chat），
    后来用户用简历项目名又绑了一次（Echo AI 助手），旧记录会被清掉，
    否则 all_contexts 会把同一份代码算两遍。
    """
    CODE_DIR.mkdir(parents=True, exist_ok=True)

    # 清掉指向同一目录的旧记录
    current = _path_key(scan.path)
    for old in CODE_DIR.glob("*.json"):
        try:
            d = json.loads(old.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if _path_key(d.get("path", "")) == current:
            old.unlink(missing_ok=True)

    # 没指定就退回目录名
    label = project_name.strip() or scan.name
    slug = _slug(label)

    payload = {
        **scan.to_dict(),
        "project_name": label,
        "slug": slug,
        # 摘要里用简历项目名，不暴露目录名
        "summary": scan.summary_markdown(max_chars=6000, display_name=label),
        "scanned_at": __import__("time").time(),
    }
    (CODE_DIR / f"{slug}.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return payload


def list_saved() -> list[dict]:
    """列出已保存的项目代码，按扫描时间倒序。"""
    if not CODE_DIR.exists():
        return []
    out: list[dict] = []
    for p in CODE_DIR.glob("*.json"):
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        out.append(
            {
                "slug": d.get("slug", p.stem),
                "project_name": d.get("project_name") or d.get("name", ""),
                "name": d.get("name", ""),
                "path": d.get("path", ""),
                "file_count": d.get("file_count", 0),
                "line_count": d.get("line_count", 0),
                "langs": d.get("langs", {}),
                "deps": (d.get("deps") or [])[:12],
                "scanned_at": d.get("scanned_at", 0),
            }
        )
    return sorted(out, key=lambda x: -x.get("scanned_at", 0))


def delete_saved(slug: str) -> bool:
    p = CODE_DIR / f"{_slug(slug)}.json"
    if p.exists():
        p.unlink()
        return True
    return False


def get_context(project_name: str, max_chars: int = 3500) -> str:
    """按简历项目名取代码摘要（供改写 prompt 使用）。

    先精确匹配，再退化到「包含」匹配，方便用户写的项目名不完全是目录名。
    """
    if not CODE_DIR.exists():
        return ""
    target = _slug(project_name)
    exact = CODE_DIR / f"{target}.json"
    if exact.exists():
        try:
            d = json.loads(exact.read_text(encoding="utf-8"))
            return (d.get("summary") or "")[:max_chars]
        except (OSError, json.JSONDecodeError):
            return ""

    # 模糊匹配：项目名互相包含
    for p in CODE_DIR.glob("*.json"):
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        label = d.get("project_name") or d.get("name") or ""
        if label and (label in project_name or project_name in label):
            return (d.get("summary") or "")[:max_chars]
    return ""


def all_contexts(max_chars: int = 3000, only_projects: list[str] | None = None) -> str:
    """把所有已保存项目的摘要拼起来（改写时不指定项目时用）。

    - 按路径去重：历史数据里同一个目录可能存过两条
    - only_projects 非空时只拼这些项目（传简历里的项目名列表，
      避免把简历里根本没有的项目代码也塞给模型）
    """
    items = list_saved()
    if not items:
        return ""

    allow = {n.strip() for n in only_projects} if only_projects else None

    seen_paths: set[str] = set()
    parts: list[str] = []
    for it in items:
        if allow is not None and it["project_name"].strip() not in allow:
            continue
        key = _path_key(it.get("path", ""))
        if key in seen_paths:
            continue
        seen_paths.add(key)
        ctx = get_context(it["project_name"], max_chars=800)
        if ctx:
            parts.append(ctx)
        if len(parts) >= 5:
            break

    return "\n\n---\n\n".join(parts)[:max_chars]
