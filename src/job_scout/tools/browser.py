"""浏览器执行层。

设计要点（也是面试能讲的东西）：

1. `BrowserDriver` 是「插座标准」——上层代码只依赖这几个方法，
   不关心底下是 Playwright 还是视觉模型。
2. `PlaywrightDriver` 是当前唯一实现：用 Chrome 调试协议直接操作页面。
3. 将来如果被风控拦了，补一个 `VisualDriver` 实现同样接口，
   上层一行不用改。这叫「面向接口编程」。

为什么默认用系统 Edge / Chrome 而不是 Playwright 自带 Chromium？
自带的是「Chrome for Testing」构建，UA、Client Hints、安装路径都是
自动化特征，国内站点（BOSS/实习僧）识别得很准，容易直接给空白页。
用系统装的 Edge 就是普通浏览器，特征正常。
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Protocol

from playwright.sync_api import sync_playwright


class BrowserDriver(Protocol):
    """浏览器操作的统一抽象。"""

    def open(self, url: str, timeout_ms: int = 60_000) -> None: ...
    def html(self) -> str: ...
    def text(self, selector: str) -> str: ...
    def click(self, selector: str) -> None: ...
    def wait_for(self, selector: str, timeout_ms: int = 15_000) -> bool: ...
    def wait_until(self, predicate, timeout_s: int = 300, interval_s: int = 2) -> bool: ...
    def screenshot(self, path: str | Path) -> Path: ...
    def save_html(self, path: str | Path) -> Path: ...
    def close(self) -> None: ...


class PlaywrightDriver:
    """用 Playwright 驱动系统浏览器。

    `channel` 可选：
      - "msedge"   Windows 自带 Edge（推荐）
      - "chrome"   系统装的 Chrome
      - None       回退到 Playwright 自带 Chromium（容易被识别）
    """

    def __init__(
        self,
        profile_dir: str | Path = ".playwright/profile",
        headless: bool = False,
        viewport: tuple[int, int] = (1440, 900),
        channel: str | None = "msedge",
        slow_mo: int = 0,
    ) -> None:
        Path(profile_dir).mkdir(parents=True, exist_ok=True)

        self._pw = sync_playwright().start()
        launch_kwargs = dict(
            user_data_dir=str(profile_dir),
            headless=headless,
            viewport={"width": viewport[0], "height": viewport[1]},
            locale="zh-CN",
            timezone_id="Asia/Shanghai",
            slow_mo=slow_mo,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--start-maximized",
            ],
        )

        self.channel = channel
        try:
            self._ctx = self._pw.chromium.launch_persistent_context(
                channel=channel, **launch_kwargs
            )
        except Exception as e:
            # 渠道不可用时自动降级，别直接崩
            print(f"[warn] 启动 channel={channel} 失败：{e}")
            print("[warn] 降级到 Playwright 自带 Chromium（可能被站点识别）")
            self.channel = None
            self._ctx = self._pw.chromium.launch_persistent_context(**launch_kwargs)

        self._page = self._ctx.pages[0] if self._ctx.pages else self._ctx.new_page()

    # ---- BrowserDriver 实现 ----

    def open(self, url: str, timeout_ms: int = 60_000) -> None:
        self._page.goto(url, wait_until="load", timeout=timeout_ms)
        # SPA 首屏还要再等一会儿，但别死等，超时就继续
        try:
            self._page.wait_for_load_state("networkidle", timeout=10_000)
        except Exception:
            pass

    def html(self) -> str:
        return self._page.content()

    def text(self, selector: str) -> str:
        el = self._page.query_selector(selector)
        return el.inner_text() if el else ""

    def click(self, selector: str) -> None:
        self._page.click(selector)

    def wait_for(self, selector: str, timeout_ms: int = 15_000) -> bool:
        try:
            self._page.wait_for_selector(selector, timeout=timeout_ms)
            return True
        except Exception:
            return False

    def wait_until(self, predicate, timeout_s: int = 300, interval_s: int = 2) -> bool:
        deadline = time.time() + timeout_s
        while time.time() < deadline:
            try:
                if predicate():
                    return True
            except Exception:
                pass
            time.sleep(interval_s)
        return False

    def screenshot(self, path: str | Path) -> Path:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        self._page.screenshot(path=str(p), full_page=False)
        return p

    def save_html(self, path: str | Path) -> Path:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(self.html(), encoding="utf-8")
        return p

    def close(self) -> None:
        self._ctx.close()
        self._pw.stop()

    # ---- 诊断用 ----

    def body_text(self) -> str:
        """整页可见文本，用来判断当前处在什么状态。"""
        try:
            return self._page.inner_text("body")
        except Exception:
            return ""

    def count(self, selector: str) -> int:
        try:
            return self._page.locator(selector).count()
        except Exception:
            return 0

    def page_info(self) -> dict[str, object]:
        """出问题时报这个，比干瞪眼强。"""
        try:
            title = self._page.title()
        except Exception:
            title = "<取不到>"
        try:
            body = self._page.inner_text("body")
        except Exception:
            body = ""
        return {
            "url": self._page.url,
            "title": title,
            "body_len": len(body),
            "body_head": body.strip()[:120].replace("\n", " "),
            "channel": self.channel,
        }
