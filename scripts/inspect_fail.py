"""分析失败样本 HTML，看它到底是什么页面。"""

from __future__ import annotations

from pathlib import Path

from bs4 import BeautifulSoup

p = Path("data/raw/fail_sample.html")
html = p.read_text(encoding="utf-8", errors="ignore")
soup = BeautifulSoup(html, "html.parser")

print("长度:", len(html))
print("title:", (soup.title.string if soup.title else "<无>"))

body = soup.body.get_text(" ", strip=True) if soup.body else ""
print("body 长度:", len(body))
print("body 开头:", body[:300])

print("\n关键标记:")
for kw in ("job-sec-text", "job-detail", "job-detail-section", "登录", "安全验证", "职位不存在", "已下线"):
    print(f"  {kw:<20} {kw in html}")

print("\nclass 里含 'job' 的元素（前 20 个）:")
seen = set()
for el in soup.find_all(attrs={"class": True}):
    cls = " ".join(el.get("class"))
    if "job" in cls.lower() and cls not in seen:
        seen.add(cls)
        print(f"  <{el.name} class='{cls[:80]}'>")
    if len(seen) >= 20:
        break

print("\n最后 200 字符:", html[-200:].replace("\n", " "))
