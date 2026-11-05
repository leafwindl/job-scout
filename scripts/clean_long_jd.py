"""超长 JD 清洗：>2000 字的用 LLM 抽成「职责 + 要求」。

只有 5-10 条这么长，全量跑没必要。
洗过的存进 postings.jd_clean，读的时候优先用它。
"""

from __future__ import annotations

import sqlite3
import sys

from job_scout.config import settings
from job_scout.rag.llm import get_llm
from job_scout.storage import Storage

THRESHOLD = 2000

PROMPT = """下面是一段招聘 JD 原文，可能混着公司宣传、福利介绍、创始人心声。

请只抽出**岗位职责**和**任职要求**，丢掉公司宣传。

原文：
{jd}

输出格式（纯文本，不要 markdown 代码块、不要解释）：
【岗位职责】
1. ……
2. ……

【任职要求】
1. ……
2. ……

【加分项】
1. ……（没有就省略这一段）

规则：
- 只抽取原文有的内容，禁止补充
- 每条压缩到一句话，保留原文的技术名词和数字
- 硬性门槛（学历、年级、每周天数、实习时长）必须保留
- 总共不超过 900 字"""


def clean_one(jd: str, llm) -> str:
    if len(jd) <= THRESHOLD:
        return ""
    try:
        raw = llm.complete("你是一个招聘信息整理助手，只做抽取不做发挥。", PROMPT.format(jd=jd), temperature=0.1)
    except Exception as e:  # noqa: BLE001
        print(f"  失败：{type(e).__name__}: {e}")
        return ""
    text = raw.strip().strip("`").strip()
    # 兜底：清洗后反而更长就不采用
    if not text or len(text) > len(jd):
        return ""
    return text[:4000]


def main() -> None:
    apply = "--yes" in sys.argv
    llm = get_llm()
    if llm is None:
        raise SystemExit("没配置模型 Key")

    # 先过一遍 Storage，触发 MIGRATIONS 把 jd_clean 列补上
    Storage(settings.db_path).close()

    conn = sqlite3.connect(settings.db_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT job_id, title, description, jd_clean FROM postings "
        "WHERE description IS NOT NULL AND length(description) > ? "
        "AND (jd_clean IS NULL OR jd_clean = '')",
        (THRESHOLD,),
    ).fetchall()

    print(f"需要清洗的超长 JD：{len(rows)} 条（>{THRESHOLD} 字）")
    if not rows:
        conn.close()
        return

    done = 0
    for r in rows:
        jd = r["description"] or ""
        print(f"\n[{r['title'][:32]}] {len(jd)} 字")
        cleaned = clean_one(jd, llm)
        if not cleaned:
            continue
        print(f"  → 清洗后 {len(cleaned)} 字")
        print(f"  {cleaned[:120].replace(chr(10), ' ')}")
        if apply:
            conn.execute(
                "UPDATE postings SET jd_clean = ? WHERE job_id = ?", (cleaned, r["job_id"])
            )
            done += 1

    if apply:
        conn.commit()
        print(f"\n✓ 已写入 {done} 条")
    else:
        print("\n预览模式，加 --yes 写入")
    conn.close()


if __name__ == "__main__":
    main()
