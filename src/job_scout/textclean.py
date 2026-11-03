"""JD 文本清洗。

抓取端已经改用 innerText（只读可见文本），但历史数据里混进了三类脏东西：

1. 内联 `<style>` 的 CSS 规则（`.xxx{display:none!important;}` 之类）
2. 反爬水印词，插在字词之间：「职**kanzhun**位描述」「实**boss**习」「2028**直聘**年」
3. 抓取时带下来的固定杂质：「微信扫码分享」「举报」「职位描述」「来自BOSS直聘」

难点是「直聘」既是水印也是正常公司名（BOSS直聘）。
做法：**先把正常写法保护起来（占位符），删完水印再还原**。
"""

from __future__ import annotations

import re

# CSS 规则：.className{...}
_CSS_RULE = re.compile(r"\.[\w-]+\s*\{[^{}]*\}")
_STYLE_TAG = re.compile(r"<style[^>]*>.*?</style>", re.S | re.I)

# 需要保护的正常写法（含「直聘」二字）
_PROTECT = ("BOSS直聘", "Boss直聘", "boss直聘", "Boss直聘网")

# 水印词：会插在词中间，删掉不影响语义
_WATERMARKS = ("kanzhun", "直聘", "看准", "boss")

# 抓取时带下来的固定杂质
_NOISE = ("微信扫码分享", "扫码分享", "来自BOSS直聘", "BOSS直聘举报", "举报", "职位描述")

PH = "\x00"  # 占位符


def clean_jd(text: str) -> str:
    """清洗一条 JD 正文，返回干净文本。"""
    if not text:
        return ""

    out = text

    # 1) 保护正常写法，避免「BOSS直聘」被当成水印删掉
    for i, w in enumerate(_PROTECT):
        out = out.replace(w, f"{PH}{i}{PH}")

    # 2) 去掉 <style> 标签和其中的 CSS 规则
    out = _STYLE_TAG.sub(" ", out)
    out = _CSS_RULE.sub(" ", out)
    out = re.sub(r"\.[A-Za-z][\w-]*\s*\{[^{}]*\}", " ", out)

    # 3) 删水印词（已保护的正常写法不受影响）
    for w in _WATERMARKS:
        out = out.replace(w, "")

    # 4) 删固定杂质
    for w in _NOISE:
        out = out.replace(w, "")

    # 5) 还原保护词
    for i, w in enumerate(_PROTECT):
        out = out.replace(f"{PH}{i}{PH}", w)

    # 6) 空白规整
    out = out.replace("\u200b", "").replace("\u00ad", "")
    out = re.sub(r"[ \t\u3000]+", " ", out)
    out = re.sub(r"\n{3,}", "\n\n", out)

    return out.strip()


def is_dirty(text: str) -> bool:
    """判断一条数据是否需要清洗（用于批量筛选）。

    注意：「BOSS直聘」是正常公司名，「{」可能是正文里的代码示例，都不算脏。
    """
    if not text:
        return False
    if _CSS_RULE.search(text) or _STYLE_TAG.search(text):
        return True
    if "kanzhun" in text:
        return True
    # 直聘后面紧跟汉字/数字，且前面没有 BOSS，说明是水印
    return bool(re.search(r"(?<!BOSS)直聘(?=[\u4e00-\u9fff0-9])", text))
