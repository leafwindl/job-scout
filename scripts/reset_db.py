"""清空数据库（先备份）。"""

from __future__ import annotations

import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

DB = Path("data/job_scout.db")

if not DB.exists():
    print("数据库不存在:", DB)
    raise SystemExit(0)

backup = Path("data") / f"job_scout_backup_{datetime.now():%Y%m%d_%H%M%S}.db"
shutil.copy2(DB, backup)
print("已备份 ->", backup)

conn = sqlite3.connect(DB)
before = conn.execute("SELECT COUNT(*) FROM postings").fetchone()[0]
conn.execute("DELETE FROM postings")
conn.execute("DELETE FROM runs")
conn.commit()
after = conn.execute("SELECT COUNT(*) FROM postings").fetchone()[0]
conn.execute("VACUUM")
conn.close()

print(f"清空完成：{before} -> {after}")
