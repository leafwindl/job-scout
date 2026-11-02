"""清理测试数据。"""

from __future__ import annotations

import sqlite3

c = sqlite3.connect("data/job_scout.db")
c.execute("DELETE FROM postings WHERE job_id LIKE 'test-%' OR job_id LIKE 'jdtest-%'")
c.commit()
print("rows =", c.execute("SELECT COUNT(*) FROM postings").fetchone()[0])
c.close()
