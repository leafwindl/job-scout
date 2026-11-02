"""薪资解析。

单独成模块的原因：API 服务也要用这个函数，但它不该为了一个纯函数
把整个采集栈（bs4 / playwright）拖进依赖里。
"""

from __future__ import annotations

import re


def parse_salary(raw: str) -> tuple[float | None, float | None]:
    """'15-25K' / '15-25K·13薪' / '200-300元/天' -> (15.0, 25.0)。

    目前只处理「K」区间；日薪 / 面议返回 (None, None)。
    """
    if not raw:
        return None, None
    nums = re.findall(r"(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)\s*[Kk千]", raw)
    if nums:
        return float(nums[0][0]), float(nums[0][1])
    return None, None
