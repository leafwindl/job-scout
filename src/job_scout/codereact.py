"""ReAct 读代码：让模型自己决定读哪些文件。

两个使用场景：
1. prescan_project —— 关联文件夹时预扫描，20 轮，摸清项目技术偏向和大致结构
2. analyze_for_job —— 改简历时按岗位分析，12 轮，只找与岗位相关的实现

两者共用同一套工具和循环，区别只在开场 prompt 和轮次上限。

设计要点：
- 用原生 function calling（实测 60+ 次调用零格式错误）
- 开场直接给文件树，省掉前几轮探索；list_dir 最多 2 次
- 只读沙箱：所有路径限制在项目根内
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path

# ==================== 工具定义 ====================

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "list_dir",
            "description": "列出目录内容。文件树已经给了，只在需要看某个子目录全貌时调用。",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string", "description": "相对项目根的路径"}},
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "读文件内容，最多返回 300 行。文件更长时用 start 续读。",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "相对项目根的文件路径"},
                    "start": {"type": "integer", "description": "起始行，从 1 开始"},
                    "end": {"type": "integer", "description": "结束行（含）"},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "grep",
            "description": "在项目源码里搜索字符串，返回 文件:行号 + 该行内容。",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "要搜的字符串"},
                    "max": {"type": "integer", "description": "最多返回几条，默认 10"},
                },
                "required": ["pattern"],
            },
        },
    },
]

SKIP_DIRS = {
    ".git", ".venv", "venv", "node_modules", "__pycache__", ".next", "dist",
    "build", ".pytest_cache", ".ruff_cache", ".playwright", "site-packages",
    "target", "vendor", ".turbo", ".cache", "artifacts", "coverage",
}

CODE_EXT = {
    ".py", ".ts", ".tsx", ".js", ".jsx", ".vue", ".java", ".kt", ".go", ".rs",
    ".cs", ".rb", ".php", ".swift", ".sql", ".dart",
}

MAX_LINES_PER_READ = 300
MAX_TOOL_RESULT = 6000
MAX_CONTEXT_CHARS = 90_000  # 到这就强制收尾（约 45K token）


@dataclass
class ReactResult:
    """一次 ReAct 运行的结果。"""

    text: str = ""
    turns: int = 0
    tool_calls: int = 0
    files_read: int = 0
    elapsed: float = 0.0
    context_chars: int = 0
    trace: list[dict] = field(default_factory=list)
    error: str = ""

    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "turns": self.turns,
            "tool_calls": self.tool_calls,
            "files_read": self.files_read,
            "elapsed": round(self.elapsed, 1),
            "context_chars": self.context_chars,
            "trace": self.trace,
            "error": self.error,
        }


# ==================== 只读沙箱 ====================


class Sandbox:
    def __init__(self, root: str | Path) -> None:
        # 存档里的路径是宿主格式（F:\xxx），容器里要映射到 /host/f/xxx，
        # 否则所有 read_file 都会「文件不存在」，模型只能干调 grep。
        from job_scout.codebase import resolve_host_path

        self.root = Path(resolve_host_path(str(root))).resolve()
        self.trace: list[dict] = []
        self.files_read = 0
        self.list_dir_calls = 0

    def _safe(self, rel: str) -> Path | None:
        try:
            full = (self.root / (rel or ".")).resolve()
        except (OSError, ValueError):
            return None
        if not str(full).startswith(str(self.root)):
            return None
        return full

    def list_dir(self, path: str) -> str:
        self.list_dir_calls += 1
        full = self._safe(path)
        if full is None or not full.is_dir():
            return f"错误：目录不存在或越界：{path}"
        items: list[str] = []
        try:
            for child in sorted(full.iterdir(), key=lambda p: p.name.lower()):
                if child.name in SKIP_DIRS or child.name.startswith("."):
                    continue
                if child.is_dir():
                    items.append(f"{child.name}/")
                elif child.suffix.lower() in CODE_EXT:
                    items.append(child.name)
                if len(items) >= 60:
                    items.append("...")
                    break
        except PermissionError:
            return "错误：没有权限"
        rel = full.relative_to(self.root)
        head = "（项目根）" if str(rel) == "." else f"{rel}/"
        return f"{head}\n" + "\n".join(items) if items else f"{head}\n（空目录）"

    def read_file(self, path: str, start: int = 1, end: int | None = None) -> str:
        full = self._safe(path)
        if full is None or not full.is_file():
            return f"错误：文件不存在或越界：{path}"
        self.files_read += 1
        try:
            text = full.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            return "错误：读不了这个文件"
        lines = text.splitlines()
        total = len(lines)
        s = max(1, start)
        e = min(end or s + MAX_LINES_PER_READ - 1, s + MAX_LINES_PER_READ - 1, total)
        body = "\n".join(lines[s - 1 : e])
        note = ""
        if e < total:
            note = f"\n\n…共 {total} 行，还有 {total - e} 行。要的话用 start={e + 1} 续读"
        return f"[{path} 第 {s}-{e} 行 / 共 {total} 行]\n{body}{note}"[:MAX_TOOL_RESULT]

    def grep(self, pattern: str, max_hits: int = 10) -> str:
        if not pattern:
            return "错误：pattern 不能为空"
        hits: list[str] = []
        scanned = 0
        for dirpath, dirnames, filenames in os.walk(self.root):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")]
            for name in filenames:
                if Path(name).suffix.lower() not in CODE_EXT:
                    continue
                scanned += 1
                if scanned > 3000:
                    break
                try:
                    text = (Path(dirpath) / name).read_text(encoding="utf-8", errors="ignore")
                except OSError:
                    continue
                for i, line in enumerate(text.splitlines(), 1):
                    if pattern in line:
                        rel = (Path(dirpath) / name).relative_to(self.root)
                        hits.append(f"{rel}:{i}  {line.strip()[:120]}")
                        if len(hits) >= max_hits:
                            break
                if len(hits) >= max_hits:
                    break
            if len(hits) >= max_hits:
                break
        return "\n".join(hits) if hits else f"没搜到 {pattern!r}"

    def run(self, name: str, args: dict) -> str:
        t0 = time.time()
        try:
            if name == "list_dir":
                out = self.list_dir(args.get("path", ""))
            elif name == "read_file":
                out = self.read_file(args.get("path", ""), int(args.get("start", 1)), args.get("end"))
            elif name == "grep":
                out = self.grep(args.get("pattern", ""), int(args.get("max", 10)))
            else:
                out = f"错误：未知工具 {name}"
        except Exception as e:  # noqa: BLE001
            out = f"错误：{type(e).__name__}: {e}"
        self.trace.append(
            {"tool": name, "args": args, "ms": int((time.time() - t0) * 1000)}
        )
        return out


# ==================== ReAct 循环 ====================


def react_run(
    root: str | Path,
    system: str,
    opening: str,
    llm,
    max_turns: int = 12,
    max_list_dir: int = 2,
    temperature: float = 0.2,
) -> ReactResult:
    """跑一轮 ReAct，返回最终文本。"""
    box = Sandbox(root)
    messages: list[dict] = [
        {"role": "system", "content": system},
        {"role": "user", "content": opening},
    ]
    res = ReactResult()
    t0 = time.time()

    try:
        finished = False
        for turn in range(max_turns):
            res.turns = turn + 1

            # 快超上下文预算了，提前收尾
            ctx = sum(len(str(m.get("content") or "")) for m in messages)
            if ctx > MAX_CONTEXT_CHARS:
                messages.append(
                    {"role": "user", "content": "上下文预算快满了，立刻停止调用工具并输出结论。"}
                )
                break

            msg = llm.chat(messages, tools=TOOLS, temperature=temperature)

            if not msg.tool_calls:
                messages.append({"role": "assistant", "content": msg.content or ""})
                finished = True
                break

            messages.append(
                {
                    "role": "assistant",
                    "content": msg.content or "",
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            },
                        }
                        for tc in msg.tool_calls
                    ],
                }
            )

            for tc in msg.tool_calls:
                res.tool_calls += 1
                name = tc.function.name
                try:
                    args = json.loads(tc.function.arguments or "{}")
                except json.JSONDecodeError:
                    args = {}

                # 限制 list_dir 次数：文件树已经给了，别一直翻目录
                if name == "list_dir" and box.list_dir_calls >= max_list_dir:
                    out = "提示：list_dir 已经用过 2 次，请直接用 read_file / grep 读具体文件。"
                else:
                    out = box.run(name, args)

                messages.append({"role": "tool", "tool_call_id": tc.id, "content": out})

        if not finished:
            messages.append(
                {
                    "role": "user",
                    "content": "轮次用完了，现在直接按要求的格式输出结论，不要再调用工具。",
                }
            )
            msg = llm.chat(messages, temperature=temperature)
            messages.append({"role": "assistant", "content": msg.content or ""})

    except Exception as e:  # noqa: BLE001
        res.error = f"{type(e).__name__}: {e}"

    res.elapsed = time.time() - t0
    res.files_read = box.files_read
    res.trace = box.trace
    res.context_chars = sum(len(str(m.get("content") or "")) for m in messages)
    res.text = (messages[-1].get("content") or "") if messages else ""
    return res


# ==================== 场景一：预扫描 ====================

PRESCAN_SYSTEM = """你是一个读代码很准的技术分析师。你在给一个代码项目做「技术画像」，
结果会写进求职者的简历项目库。

工作方式：
- 用工具读代码，不要凭猜测
- 文件树已经给了，先用最少次数确认整体结构，然后集中读核心文件
- 优先读：入口文件、核心业务模块、关键实现
- 跳过：测试、配置、脚本、文档、生成的代码

输出格式（Markdown，不要多余前言）：
## 技术偏向
一句话定性这个项目属于什么方向（如「RAG 检索增强」「多智能体编排」「移动端 + 后端全栈」），
再列 3-5 个最能代表它的技术关键词。

## 项目结构
按层次说清楚：分几层/几个子系统，每层用什么技术栈，各自负责什么。
不要罗列文件名，要说「XX 层用 YY 实现 ZZ」。

## 核心实现
2-4 个最有技术含量的实现，每个说清：做了什么、怎么做的、为什么这么做。
要具体到机制（状态机、降级路径、并发控制、缓存策略这种级别的描述）。

## 适合投什么岗位
基于上面的技术画像，判断这个项目最适合讲给什么方向的岗位听，2-3 个方向。"""


def prescan_project(root: str | Path, name: str, tree: list[str], llm, max_turns: int = 20) -> ReactResult:
    """预扫描：摸清项目技术偏向和结构（20 轮）。"""
    opening = f"""项目：{name}
根目录：{root}

【文件树】（前 60 条，完整路径）
{chr(10).join(tree[:60])}

按输出格式给出技术画像。最多 {max_turns} 轮。"""
    return react_run(root, PRESCAN_SYSTEM, opening, llm, max_turns=max_turns, max_list_dir=2)


# ==================== 场景二：按岗位分析 ====================

JOB_SYSTEM = """你在帮求职者改写简历里的一个项目，目标是让这段描述更贴目标岗位。

工作方式：
- 用工具读代码，不要凭猜测
- 文件树已经给了，先判断哪些模块和岗位相关，然后集中读那几个
- 优先找「岗位要求里提到、但简历里没写透」的实现
- 跳过与岗位无关的模块、测试、配置

输出格式（Markdown，不要多余前言）：
## 与岗位相关的实现
3-5 条，每条：做了什么（贴 JD 的用词）+ 代码里在哪 + 怎么实现的。

## 简历需要修正的地方
2-3 条：简历里写得不准、写虚了、或者明明有代码支撑却没写透的点。
格式：简历原文 → 问题 → 依据代码应该怎么说。

## 改写建议
2-3 条，直接给出可用的句子：
- 原文：……
- 改后：……
- 依据：代码里的什么

注意：只能引用代码里真实存在的东西，不要编造。句子要像人写的，不要出现「X 个文件」「X 万行」。"""


def analyze_for_job(
    root: str | Path,
    name: str,
    tree: list[str],
    jd_core: str,
    project_desc: str,
    llm,
    max_turns: int = 12,
) -> ReactResult:
    """按岗位分析：只找与岗位相关的实现，直接产出改写建议（12 轮）。"""
    opening = f"""【目标岗位要求】
{jd_core or '（没拿到 JD）'}

【简历里这个项目的描述】
{project_desc or '（简历里没写这个项目）'}

【项目】{name}
根目录：{root}

【文件树】（前 60 条）
{chr(10).join(tree[:60])}

按输出格式分析。最多 {max_turns} 轮，读到够用就停。"""
    return react_run(root, JOB_SYSTEM, opening, llm, max_turns=max_turns, max_list_dir=2)


def analysis_markdown(react: ReactResult, title: str) -> str:
    """把 ReAct 结果包成可存档的段落头。"""
    head = f"<!-- {title}｜{react.turns} 轮 / {react.tool_calls} 次调用 / {react.elapsed:.0f}s -->"
    return f"{head}\n{react.text}".strip()
