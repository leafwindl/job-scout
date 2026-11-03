"""扫描 JD 正文里的异常字符，判断乱码类型。"""

from __future__ import annotations

import sqlite3
import unicodedata
from collections import Counter

conn = sqlite3.connect("data/job_scout.db")
conn.row_factory = sqlite3.Row
rows = conn.execute(
    "SELECT job_id, title, description FROM postings "
    "WHERE description IS NOT NULL AND description != ''"
).fetchall()
conn.close()

print(f"共 {len(rows)} 条 JD\n")

# 分类收集
pua = Counter()          # 私有区字符 U+E000–U+F8FF
control = Counter()      # 控制字符
replacement = 0          # U+FFFD 替换符
zero_width = Counter()   # 零宽字符
weird = Counter()        # 其它非中英文数字标点

ZH_RANGES = [(0x4E00, 0x9FFF), (0x3400, 0x4DBF)]
ALLOWED_PUNCT = set("，。、；：？！“”‘’（）《》【】—…·～％￥+-/*=<>()[]{}.,:;!?\"'@#&_|\\~^`$%°")

for r in rows:
    text = r["description"] or ""
    for ch in text:
        cp = ord(ch)
        if 0xE000 <= cp <= 0xF8FF:
            pua[ch] += 1
        elif cp == 0xFFFD:
            replacement += 1
        elif unicodedata.category(ch) in ("Cc", "Cf") and ch not in "\n\t":
            control[ch] += 1
        elif ch in ("\u200b", "\u200c", "\u200d", "\ufeff", "\u00ad"):
            zero_width[ch] += 1
        elif cp < 128 or 0x4E00 <= cp <= 0x9FFF:
            continue
        elif ch in ALLOWED_PUNCT:
            continue
        elif unicodedata.category(ch).startswith(("L", "N", "P", "S")):
            continue
        else:
            weird[ch] += 1

print("=== 私有区字符（字体加密的典型特征）===")
if pua:
    print(f"  不同字符 {len(pua)} 个，总出现 {sum(pua.values())} 次")
    for ch, n in pua.most_common(20):
        print(f"    U+{ord(ch):04X} {unicodedata.name(ch, '?')}  x{n}  {ch!r}")
else:
    print("  无")

print("\n=== 替换符 U+FFFD ===")
print(f"  {replacement} 次")

print("\n=== 零宽字符 ===")
if zero_width:
    for ch, n in zero_width.items():
        print(f"    U+{ord(ch):04X} x{n}")
else:
    print("  无")

print("\n=== 控制字符 ===")
if control:
    for ch, n in control.most_common(10):
        print(f"    U+{ord(ch):04X} x{n}")
else:
    print("  无")

print("\n=== 其它非常见字符 ===")
if weird:
    for ch, n in weird.most_common(15):
        print(f"    U+{ord(ch):04X} {unicodedata.category(ch)} x{n}  {ch!r}")
else:
    print("  无")

# 抽样看一条有 PUA 的 JD
if pua:
    print("\n=== 带私有区字符的 JD 样例 ===")
    for r in rows:
        text = r["description"] or ""
        if any(0xE000 <= ord(c) <= 0xF8FF for c in text):
            print(f"  [{r['title']}]")
            print(f"  {text[:300]}")
            break
