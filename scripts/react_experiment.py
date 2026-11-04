"""ReAct 读代码实验：用原生 Function Calling。

跑真实项目，看轮次、耗时、输出质量。
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

from job_scout.rag.llm import get_llm

# ==================== 工具定义 ====================

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "list_dir",
            "description": "列出目录内容。path 为空字符串表示项目根目录。",
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
            "description": "读文件内容。返回最多 300 行；文件更长时用 start/end 续读。",
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
    "target", "vendor", ".turbo", ".cache", "artifacts",
}
CODE_EXT = {
    ".py", ".ts", ".tsx", ".js", ".jsx", ".vue", ".java", ".kt", ".go", ".rs",
    ".cs", ".rb", ".php", ".swift", ".sql", ".dart",
}
MAX_LINES = 300
MAX_TOOL_RESULT = 6000


class Sandbox:
    """只读沙箱：所有路径限制在项目根内。"""

    def __init__(self, root: str) -> None:
        self.root = Path(root).resolve()
        self.trace: list[dict] = []
        self.reads = 0

    def _safe(self, rel: str) -> Path | None:
        try:
            full = (self.root / rel).resolve()
        except (OSError, ValueError):
            return None
        if not str(full).startswith(str(self.root)):
            return None
        return full

    def list_dir(self, path: str) -> str:
        full = self._safe(path or ".")
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
        self.reads += 1
        try:
            text = full.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            return "错误：读不了这个文件"
        lines = text.splitlines()
        total = len(lines)
        s = max(1, start)
        e = end or (s + MAX_LINES - 1)
        e = min(e, s + MAX_LINES - 1, total)
        body = "\n".join(lines[s - 1 : e])
        note = ""
        if total > MAX_LINES and e < total:
            note = f"\n\n…共 {total} 行，还有 {total - e} 行。需要的话用 start={e + 1} 续读"
        return f"[{path} 第 {s}-{e} 行 / 共 {total} 行]\n{body}{note}"[:MAX_TOOL_RESULT]

    def grep(self, pattern: str, max_hits: int = 10) -> str:
        hits: list[str] = []
        scanned = 0
        for dirpath, dirnames, filenames in os.walk(self.root):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")]
            for name in filenames:
                if Path(name).suffix.lower() not in CODE_EXT:
                    continue
                p = Path(dirpath) / name
                scanned += 1
                if scanned > 3000:
                    break
                try:
                    text = p.read_text(encoding="utf-8", errors="ignore")
                except OSError:
                    continue
                for i, line in enumerate(text.splitlines(), 1):
                    if pattern in line:
                        rel = p.relative_to(self.root)
                        hits.append(f"{rel}:{i}  {line.strip()[:120]}")
                        if len(hits) >= max_hits:
                            break
                if len(hits) >= max_hits:
                    break
            if len(hits) >= max_hits:
                break
        if not hits:
            return f"没搜到 {pattern!r}"
        return "\n".join(hits)

    def run(self, name: str, args: dict) -> str:
        t0 = time.time()
        try:
            if name == "list_dir":
                out = self.list_dir(args.get("path", ""))
            elif name == "read_file":
                out = self.read_file(
                    args.get("path", ""), args.get("start", 1), args.get("end")
                )
            elif name == "grep":
                out = self.grep(args.get("pattern", ""), args.get("max", 10))
            else:
                out = f"错误：未知工具 {name}"
        except Exception as e:  # noqa: BLE001
            out = f"错误：{type(e).__name__}: {e}"
        self.trace.append({"tool": name, "args": args, "ms": int((time.time() - t0) * 1000)})
        return out


SYSTEM = """你在读一个代码项目，为简历生成准确的项目描述。

规则：
- 用提供的工具读代码，不要凭猜测
- 先看目录结构判断项目分几层，再读入口和核心模块
- 遇到关键实现（接口、协议、状态机）要追进去看
- 觉得信息足够了就停止调用工具，直接输出结论

输出格式（Markdown）：
## 项目定位
一句话说清做什么、给谁用、解决什么问题。

## 技术架构
分几层、每层用什么技术，一两句话。

## 核心模块
3-5 个，每个说清「负责什么 + 怎么实现的」，不要只写文件名。

## 技术亮点
2-3 个具体做法，能看出工程判断的那种。

## 规模
文件数和行数，一句话。"""


def run_react(project_path: str, project_name: str, max_turns: int = 8) -> dict:
    llm = get_llm()
    if llm is None:
        raise SystemExit("没配置 Key")

    box = Sandbox(project_path)
    messages: list[dict] = [
        {"role": "system", "content": SYSTEM},
        {
            "role": "user",
            "content": (
                f"分析项目：{project_name}\n"
                f"根目录：{project_path}\n\n"
                "用工具读代码，读完直接按模板输出描述。"
            ),
        },
    ]

    t0 = time.time()
    turns = 0
    tool_calls = 0
    error = ""

    try:
        for turn in range(max_turns):
            turns = turn + 1
            msg = llm.chat(messages, tools=TOOLS, temperature=0.2)

            # 没有工具调用 = 它要输出结论了
            if not msg.tool_calls:
                messages.append({"role": "assistant", "content": msg.content or ""})
                break

            # 把 assistant 的 tool_calls 原样追加（协议要求）
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

            # 逐个执行工具并追加结果
            for tc in msg.tool_calls:
                tool_calls += 1
                try:
                    args = json.loads(tc.function.arguments or "{}")
                except json.JSONDecodeError:
                    args = {}
                out = box.run(tc.function.name, args)
                messages.append(
                    {"role": "tool", "tool_call_id": tc.id, "content": out}
                )
        else:
            # 跑满轮次还没出结论
            messages.append(
                {"role": "user", "content": "轮次用完了，现在直接按模板输出描述，不要再调工具。"}
            )
            msg = llm.chat(messages, temperature=0.2)
            messages.append({"role": "assistant", "content": msg.content or ""})
    except Exception as e:  # noqa: BLE001
        error = f"{type(e).__name__}: {e}"

    elapsed = time.time() - t0
    final = messages[-1].get("content", "") if messages else ""
    ctx_chars = sum(len(str(m.get("content") or "")) for m in messages)

    return {
        "project": project_name,
        "turns": turns,
        "tool_calls": tool_calls,
        "elapsed": elapsed,
        "reads": box.reads,
        "context_chars": ctx_chars,
        "final": final,
        "trace": box.trace,
        "error": error,
    }


if __name__ == "__main__":
    import sys

    MAX_TURNS = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    PROJECTS = [
        ("F:/Project_do/Agent/job-scout", "AI 求职助手"),
        ("F:/project_work/AI_Chat", "Echo AI 助手 App"),
    ]
    for path, name in PROJECTS:
        print("=" * 78)
        print(f"项目：{name}　上限 {MAX_TURNS} 轮")
        print("=" * 78)
        r = run_react(path, name, max_turns=MAX_TURNS)
        print(f"轮次 {r['turns']}　工具调用 {r['tool_calls']} 次　读文件 {r['reads']} 个")
        print(f"耗时 {r['elapsed']:.1f} 秒　上下文 {r['context_chars']} 字符")
        if r["error"]:
            print(f"错误：{r['error']}")
        print("\n--- 调用轨迹 ---")
        for t in r["trace"]:
            arg = t["args"].get("path") or t["args"].get("pattern") or ""
            print(f"  {t['tool']:<10} {str(arg)[:46]:<48} {t['ms']}ms")
        print("\n--- 输出 ---")
        print(r["final"][:2600])
        print()
