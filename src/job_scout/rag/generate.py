"""生成层：把检索到的岗位片段组装成带引用的回答。

三条硬规则（防幻觉）：
1. 只依据给定片段，不允许引用外部知识
2. 每个结论必须标来源编号
3. 片段里没有的，明确说「没有找到」，不硬答

没有 LLM 时降级为「抽取式回答」：直接列出岗位与关键要求，
并标明这是检索结果而非生成结果。保证无 key 也能演示。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from job_scout.rag.corpus import Doc

SYSTEM_PROMPT = """你是招聘信息助手。你只能依据下面给出的岗位片段回答问题。

规则：
1. 每一条结论后面必须标注来源编号，例如 [1]、[2]
2. **严禁升级措辞强度**：
   - 原文「协助 / 参与 / 配合」→ 不得写成「负责」
   - 原文「了解 / 接触 / 优先考虑」→ 不得写成「要求 / 精通 / 必须」
   - 原文「涉及 / 参与开发」→ 不得写成「要求相关经验」
3. 片段中没有的信息，必须明确说「没有找到相关岗位」，禁止编造
4. 不要编造公司名、薪资、技能要求
5. 尽可能沿用片段里的动词和限定词；关键结论用引号标出原文
6. 回答用中文，简洁，先给结论再列证据
7. **只写片段里出现过的话**。不确定某条要求是否存在时，宁可不说，也不要补充
"""

CITATION_RE = re.compile(r"\[(\d+)\]")


def build_context(docs: list[Doc], max_chars: int = 12000) -> tuple[str, list[Doc]]:
    """拼上下文，按字符预算截断，返回 (文本, 实际使用的文档)。

    按字符而非条数截断：不同 JD 长度差异大，按条数容易超预算。
    """
    lines: list[str] = []
    used: list[Doc] = []
    budget = max_chars

    for i, doc in enumerate(docs, start=1):
        desc = (doc.text.split("\n", 1)[-1] or "").strip()
        head = (
            f"[{i}] {doc.title}｜{doc.company}｜"
            f"{doc.meta.get('district') or '-'}｜{doc.meta.get('salary') or '-'}"
        )
        body = desc[:4000]  # 最长 JD 约 3200 字，基本不截断
        block = f"{head}\n{body}\n"

        if len(block) > budget:
            break
        lines.append(block)
        used.append(doc)
        budget -= len(block)

    return "\n".join(lines), used


@dataclass
class Answer:
    text: str
    citations: list[dict] = field(default_factory=list)
    mode: str = "llm"  # llm / extractive / refused
    docs_count: int = 0
    context: str = ""  # 供忠实度评测使用


def parse_citations(text: str, used: list[Doc]) -> list[dict]:
    """从回答里解析 [n]，映射回岗位。越界的编号忽略。"""
    seen: set[int] = set()
    out: list[dict] = []
    for m in CITATION_RE.finditer(text):
        idx = int(m.group(1))
        if idx in seen or not (1 <= idx <= len(used)):
            continue
        seen.add(idx)
        doc = used[idx - 1]
        out.append(
            {
                "index": idx,
                "job_id": doc.doc_id,
                "title": doc.title,
                "company": doc.company,
                "district": doc.meta.get("district") or "",
                "salary": doc.meta.get("salary") or "",
                "url": doc.meta.get("url") or "",
            }
        )
    return out


def build_user_prompt(question: str, context: str) -> str:
    return f"""岗位片段：
{context}

问题：{question}

请依据上面的片段回答，并标注来源编号。"""


def extractive_answer(question: str, used: list[Doc]) -> str:
    """无 LLM 时的降级：把检索结果结构化列出来。"""
    if not used:
        return "没有找到相关岗位。"
    lines = [f"（未接入生成模型，以下是检索到的 {len(used)} 条相关岗位）", ""]
    for i, doc in enumerate(used, start=1):
        skills = "、".join(doc.meta.get("skills", [])[:4]) or "—"
        lines.append(
            f"[{i}] {doc.title}｜{doc.company}｜"
            f"{doc.meta.get('district') or '-'}｜{doc.meta.get('salary') or '-'}"
        )
        lines.append(f"    技能：{skills}")
    return "\n".join(lines)


def ask(
    question: str,
    retriever,
    llm=None,
    k: int = 5,
    max_chars: int = 4000,
) -> Answer:
    """完整问答流程：检索 → 组装 → 生成 → 解析引用。"""
    results = retriever.search(question, k=k)
    docs = [d for d, _ in results]

    if not docs:
        return Answer(text="没有找到相关岗位。可以换个关键词，或放宽筛选条件。", mode="refused")

    context, used = build_context(docs, max_chars=max_chars)

    if llm is None:
        text = extractive_answer(question, used)
        return Answer(
            text=text,
            citations=parse_citations(text, used),
            mode="extractive",
            docs_count=len(used),
        )

    text = llm.complete(SYSTEM_PROMPT, build_user_prompt(question, context), temperature=0.0)
    return Answer(
        text=text,
        citations=parse_citations(text, used),
        mode="llm",
        docs_count=len(used),
        context=context,
    )


def _candidate_dict(i: int, doc: Doc) -> dict:
    return {
        "index": i,
        "job_id": doc.doc_id,
        "title": doc.title,
        "company": doc.company,
        "district": doc.meta.get("district") or "",
        "salary": doc.meta.get("salary") or "",
        "url": doc.meta.get("url") or "",
    }


def stream_ask(
    question: str,
    retriever,
    llm=None,
    k: int = 5,
    max_chars: int = 4000,
):
    """流式问答：依次 yield (event, payload)。

    event: meta / token / done
    - meta 先发，带上候选岗位，前端可以先渲染引用卡片占位
    - token 逐段发，前端增量渲染
    - done 带最终引用列表
    """
    results = retriever.search(question, k=k)
    docs = [d for d, _ in results]

    if not docs:
        yield "meta", {"mode": "refused", "docs": 0, "candidates": []}
        yield "token", "没有找到相关岗位。可以换个关键词，或放宽筛选条件。"
        yield "done", {"citations": []}
        return

    context, used = build_context(docs, max_chars=max_chars)
    candidates = [_candidate_dict(i, d) for i, d in enumerate(used, start=1)]
    yield "meta", {
        "mode": "llm" if llm is not None else "extractive",
        "docs": len(used),
        "candidates": candidates,
    }

    if llm is None:
        text = extractive_answer(question, used)
        yield "token", text
        yield "done", {"citations": parse_citations(text, used)}
        return

    buf: list[str] = []
    for tok in llm.stream(SYSTEM_PROMPT, build_user_prompt(question, context)):
        buf.append(tok)
        yield "token", tok
    yield "done", {"citations": parse_citations("".join(buf), used)}
