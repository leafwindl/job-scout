"""审计数据库：规模、覆盖率、采集批次、去重效果。"""

from __future__ import annotations

import sqlite3

c = sqlite3.connect("data/job_scout.db")
c.row_factory = sqlite3.Row


def scalar(sql: str) -> int:
    return c.execute(sql).fetchone()[0]


print("岗位总数   :", scalar("SELECT COUNT(*) FROM postings"))
print("有薪资     :", scalar("SELECT COUNT(*) FROM postings WHERE salary_raw <> ''"))
print("有技能     :", scalar("SELECT COUNT(*) FROM postings WHERE skills NOT IN ('[]','')"))
print("有 JD 正文 :", scalar("SELECT COUNT(*) FROM postings WHERE description IS NOT NULL AND description <> ''"))
print("有链接     :", scalar("SELECT COUNT(*) FROM postings WHERE url IS NOT NULL AND url <> ''"))
print("同 job_id  :", scalar("SELECT COUNT(DISTINCT source || ':' || job_id) FROM postings"))
print("同(公司,岗位):", scalar("SELECT COUNT(DISTINCT company || '|' || title) FROM postings"))

print("\n采集批次:")
for r in c.execute(
    "SELECT run_id, keyword, captured, new_count, updated_count, status, pages "
    "FROM runs ORDER BY started_at"
):
    print(
        f"  {r['run_id']}  {r['keyword']:<10} 响应={r['captured']:<3} "
        f"新增={r['new_count']:<3} 更新={r['updated_count']:<3} {r['status']}"
    )

print("\n重复(同公司同岗位,不同 id):")
rows = c.execute(
    "SELECT company, title, COUNT(*) n FROM postings "
    "GROUP BY company, title HAVING n > 1 ORDER BY n DESC"
).fetchall()
if not rows:
    print("  无")
for r in rows:
    print(f"  {r['n']}x  {r['company']} / {r['title']}")

c.close()
