"""SQLite 存储。

v2 相对 v1 的变化：
- postings 增加 first_seen / last_seen / last_run_id / is_active
  → 能回答「这个岗位第一次出现是什么时候」「还挂着吗」
- 新增 runs 表，每次采集记一条
  → 能回答「这次新增多少、更新多少」
- upsert 保留 first_seen，只刷新 last_seen
  → 重复采集不会把历史抹掉
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

from job_scout.constants import title_relevant
from job_scout.models import JobPosting

SCHEMA_TABLES = """
CREATE TABLE IF NOT EXISTS postings (
    source       TEXT NOT NULL,
    job_id       TEXT NOT NULL,
    title        TEXT NOT NULL,
    company      TEXT NOT NULL,
    salary_raw   TEXT,
    salary_min_k REAL,
    salary_max_k REAL,
    city         TEXT,
    district     TEXT,
    experience   TEXT,
    education    TEXT,
    skills       TEXT,
    description  TEXT,
    url          TEXT,
    collected_at TEXT,
    first_seen   TEXT,
    last_seen    TEXT,
    last_run_id  TEXT,
    is_active    INTEGER NOT NULL DEFAULT 1,
    security_id  TEXT,
    jd_attempts  INTEGER NOT NULL DEFAULT 0,
    jd_last_try  TEXT,
    is_relevant  INTEGER NOT NULL DEFAULT 1,
    jd_clean     TEXT,
    PRIMARY KEY (source, job_id)
);

CREATE TABLE IF NOT EXISTS runs (
    run_id        TEXT PRIMARY KEY,
    started_at    TEXT,
    finished_at   TEXT,
    keyword       TEXT,
    city          TEXT,
    pages         INTEGER DEFAULT 0,
    captured      INTEGER DEFAULT 0,
    new_count     INTEGER DEFAULT 0,
    updated_count INTEGER DEFAULT 0,
    status        TEXT,
    note          TEXT
);
"""

# 索引必须等老表补完列之后再建，否则会报 no such column
SCHEMA_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_postings_last_seen ON postings(last_seen);
CREATE INDEX IF NOT EXISTS idx_postings_city ON postings(city);
"""

# 老库升级时缺哪些列就补哪些
MIGRATIONS = {
    "first_seen": "TEXT",
    "last_seen": "TEXT",
    "last_run_id": "TEXT",
    "is_active": "INTEGER NOT NULL DEFAULT 1",
    "security_id": "TEXT",
    "jd_attempts": "INTEGER NOT NULL DEFAULT 0",
    "jd_last_try": "TEXT",
    "is_relevant": "INTEGER NOT NULL DEFAULT 1",
    # 超长 JD（>2000 字）用 LLM 洗过之后的精简版，读的时候优先用它
    "jd_clean": "TEXT",
}


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


class Storage:
    def __init__(self, db_path: str) -> None:
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row  # 让 fetchall() 直接能 dict()
        self.conn.executescript(SCHEMA_TABLES)
        self._migrate()          # 先补列
        self.conn.executescript(SCHEMA_INDEXES)  # 再建索引

    def _migrate(self) -> None:
        cols = {r[1] for r in self.conn.execute("PRAGMA table_info(postings)")}
        for name, decl in MIGRATIONS.items():
            if name not in cols:
                self.conn.execute(f"ALTER TABLE postings ADD COLUMN {name} {decl}")
        # 老数据补时间：用 collected_at 兜底
        self.conn.execute(
            "UPDATE postings SET first_seen = COALESCE(first_seen, collected_at), "
            "last_seen = COALESCE(last_seen, collected_at) "
            "WHERE first_seen IS NULL OR last_seen IS NULL"
        )
        self.conn.commit()

    # ---------------------------------------------------------------- 运行记录

    def start_run(self, run_id: str, keyword: str, city: str) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO runs (run_id, started_at, keyword, city, status) "
            "VALUES (?,?,?,?,'running')",
            (run_id, _now(), keyword, city),
        )
        self.conn.commit()

    def finish_run(
        self,
        run_id: str,
        *,
        pages: int = 0,
        captured: int = 0,
        new_count: int = 0,
        updated_count: int = 0,
        status: str = "ok",
        note: str = "",
    ) -> None:
        self.conn.execute(
            "UPDATE runs SET finished_at=?, pages=?, captured=?, new_count=?, "
            "updated_count=?, status=?, note=? WHERE run_id=?",
            (_now(), pages, captured, new_count, updated_count, status, note, run_id),
        )
        self.conn.commit()

    # ---------------------------------------------------------------- 岗位写入

    def upsert(self, job: JobPosting, run_id: str | None = None) -> bool:
        """写入一条岗位。返回 True 表示是新岗位，False 表示更新了已有的。

        first_seen 只在第一次插入时写，之后永远保留——
        这样你能看到「这个岗位挂了多久还没招到」。
        """
        key = job.dedupe_key
        source, job_id = key.split(":", 1)

        exists = self.conn.execute(
            "SELECT 1 FROM postings WHERE source=? AND job_id=?", (source, job_id)
        ).fetchone()

        now = job.collected_at.isoformat(timespec="seconds")
        self.conn.execute(
            """
            INSERT INTO postings (
                source, job_id, title, company, salary_raw, salary_min_k, salary_max_k,
                city, district, experience, education, skills, description, url,
                collected_at, first_seen, last_seen, last_run_id, is_active, security_id,
                is_relevant
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,1,?,?)
            ON CONFLICT(source, job_id) DO UPDATE SET
                title=excluded.title,
                company=excluded.company,
                salary_raw=COALESCE(NULLIF(excluded.salary_raw,''), postings.salary_raw),
                salary_min_k=COALESCE(excluded.salary_min_k, postings.salary_min_k),
                salary_max_k=COALESCE(excluded.salary_max_k, postings.salary_max_k),
                city=COALESCE(excluded.city, postings.city),
                district=COALESCE(excluded.district, postings.district),
                experience=COALESCE(excluded.experience, postings.experience),
                education=COALESCE(excluded.education, postings.education),
                skills=excluded.skills,
                description=COALESCE(excluded.description, postings.description),
                url=COALESCE(excluded.url, postings.url),
                collected_at=excluded.collected_at,
                last_seen=excluded.last_seen,
                last_run_id=excluded.last_run_id,
                is_active=1,
                security_id=COALESCE(excluded.security_id, postings.security_id),
                is_relevant=excluded.is_relevant
            """,
            (
                source, job_id, job.title, job.company, job.salary_raw,
                job.salary_min_k, job.salary_max_k, job.city, job.district,
                job.experience, job.education, json.dumps(job.skills, ensure_ascii=False),
                job.description, job.url, now, now, now, run_id, job.security_id,
                1 if title_relevant(job.title) else 0,
            ),
        )
        self.conn.commit()
        return exists is None

    def count(self) -> int:
        return self.conn.execute("SELECT COUNT(*) FROM postings").fetchone()[0]

    def count_pending_jd(self) -> int:
        """还没有 JD 正文的**相关**岗位数，auto 模式用它判断是否完成。"""
        return self.conn.execute(
            "SELECT COUNT(*) FROM postings "
            "WHERE (description IS NULL OR description = '') AND is_relevant = 1"
        ).fetchone()[0]

    def backfill_relevance(self) -> tuple[int, int]:
        """给历史数据补 is_relevant。返回 (相关数, 无关数)。"""
        rows = self.conn.execute("SELECT source, job_id, title FROM postings").fetchall()
        rel = irr = 0
        for r in rows:
            flag = 1 if title_relevant(r["title"]) else 0
            self.conn.execute(
                "UPDATE postings SET is_relevant = ? WHERE source = ? AND job_id = ?",
                (flag, r["source"], r["job_id"]),
            )
            if flag:
                rel += 1
            else:
                irr += 1
        self.conn.commit()
        return rel, irr

    def count_non_intern(self) -> int:
        return self.conn.execute(
            "SELECT COUNT(*) FROM postings WHERE title NOT LIKE '%实习%'"
        ).fetchone()[0]

    def mark_stale(self, days: int = 7) -> int:
        """把超过 N 天没再出现的岗位标记为停招。

        增量更新的核心：每天采集会把出现过的岗位 last_seen 刷新，
        没被刷新的说明已经下架。

        阈值不能太短——单次 daily 只跑一个关键词，其它查询的岗位
        不会刷新，阈值太短会把它们全误标。
        """
        cutoff = (datetime.now() - timedelta(days=days)).isoformat(timespec="seconds")
        cur = self.conn.execute(
            "UPDATE postings SET is_active = 0 WHERE last_seen < ? AND is_active = 1",
            (cutoff,),
        )
        self.conn.commit()
        return cur.rowcount

    def daily_stats(self, since: str) -> dict:
        """日报数据：新增 / 停招 / 总数 / 有 JD。"""
        row = self.conn.execute(
            "SELECT "
            "  SUM(CASE WHEN is_active = 1 THEN 1 ELSE 0 END), "
            "  SUM(CASE WHEN first_seen >= ? THEN 1 ELSE 0 END), "
            "  SUM(CASE WHEN is_active = 0 THEN 1 ELSE 0 END), "
            "  SUM(CASE WHEN is_active = 1 AND description IS NOT NULL "
            "           AND description != '' THEN 1 ELSE 0 END) "
            "FROM postings",
            (since,),
        ).fetchone()
        keys = ("active", "new_today", "inactive", "with_jd")
        return {k: (row[i] or 0) for i, k in enumerate(keys)}

    def delete_non_intern(self) -> int:
        """删除标题不含「实习」的岗位（清理混进来的全职）。"""
        cur = self.conn.execute("DELETE FROM postings WHERE title NOT LIKE '%实习%'")
        self.conn.commit()
        return cur.rowcount

    def pending_jd(self, limit: int = 200) -> list[dict]:
        """返回还没有 JD 正文的**相关**岗位，供脚本回填。

        只发标题相关的：导航模式每开一个页面都是风险，
        给不相干的岗位白跑一趟纯亏。
        """
        rows = self.conn.execute(
            "SELECT job_id, title, company, url, security_id, jd_attempts FROM postings "
            "WHERE (description IS NULL OR description = '') AND is_relevant = 1 "
            "ORDER BY COALESCE(jd_attempts, 0) ASC, last_seen DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]

    def bump_jd_attempts(self, job_ids: list[str]) -> int:
        """记录一次失败尝试，让这些岗位排到队尾，别老堵在前面。"""
        if not job_ids:
            return 0
        now = _now()
        n = 0
        for jid in job_ids:
            cur = self.conn.execute(
                "UPDATE postings SET jd_attempts = COALESCE(jd_attempts, 0) + 1, "
                "jd_last_try = ? WHERE job_id = ?",
                (now, jid),
            )
            n += cur.rowcount
        self.conn.commit()
        return n

    def set_description(self, job_id: str, description: str) -> bool:
        """只更新正文，不动其它字段（避免把 skills/salary 覆盖成空）。"""
        cur = self.conn.execute(
            "UPDATE postings SET description = ? WHERE job_id = ?",
            (description, job_id),
        )
        self.conn.commit()
        return cur.rowcount > 0

    def upsert_jd_only(
        self,
        job_id: str,
        description: str,
        title: str = "",
        company: str = "",
        url: str = "",
    ) -> None:
        """写正文；岗位不在库里就补一条最小记录，存在则只改正文。

        为什么单独一个方法：
        之前用整条 upsert，会把 skills / salary 覆盖成空（踩过）。
        """
        now = _now()
        self.conn.execute(
            """
            INSERT INTO postings (
                source, job_id, title, company, url, description,
                collected_at, first_seen, last_seen, is_active
            ) VALUES ('boss', ?, ?, ?, ?, ?, ?, ?, ?, 1)
            ON CONFLICT(source, job_id) DO UPDATE SET description = excluded.description
            """,
            (job_id, title or job_id, company or "", url or None, description, now, now, now),
        )
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()
