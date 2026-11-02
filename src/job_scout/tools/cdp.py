"""CDP 采集层：连接你自己启动的浏览器，旁听页面自己发出的请求。

为什么要这么设计？（参考 eatmoreduck/boss-zhipin-scraper 的经验）

1. 程序自己 launch 浏览器 → 指纹是「受控浏览器」，BOSS 直接给验证页。
2. 连到你自己启动的浏览器（CDP）→ 指纹、登录态、扩展和你平时一模一样。
3. 不注入请求，只旁听页面自己发出的 XHR → 不触发「注入式请求」风控。
4. 接口返回的 salaryDesc 是明文 → 绕过 DOM 里的字体加密。

分工：
  - `launch_browser()`  由我们拉起一个带调试端口的独立浏览器（不碰你日常的浏览器）
  - `CdpCollector`     连上去，监听响应，收集数据
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from playwright.sync_api import Page, sync_playwright

EDGE_PATHS = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]
CHROME_PATHS = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
]


def find_browser(channel: str = "msedge") -> Path:
    """找到系统浏览器的可执行文件。"""
    candidates = EDGE_PATHS if channel == "msedge" else CHROME_PATHS
    for p in candidates:
        if Path(p).exists():
            return Path(p)
    raise FileNotFoundError(
        f"没找到 {channel}。请确认已安装，或用 --channel chrome 换一个。"
    )


def launch_browser(
    channel: str = "msedge",
    profile_dir: str = ".playwright/boss-profile",
    port: int = 9222,
) -> subprocess.Popen:
    """启动一个带远程调试端口的独立浏览器。

    关键：用独立的 `--user-data-dir`，所以：
      - 不会污染你日常浏览器的登录态
      - 关掉再开，这个 profile 里的登录态还在
    """
    exe = find_browser(channel)
    profile = Path(profile_dir).resolve()
    profile.mkdir(parents=True, exist_ok=True)

    cmd = [
        str(exe),
        f"--remote-debugging-port={port}",
        f"--user-data-dir={profile}",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-popup-blocking",
        "--start-maximized",
        # 关键：不加这几组，后台标签会被 Edge 节流，
        # SPA 的定时器和请求会被推迟，表现为「页面一直空白」
        "--disable-background-timer-throttling",
        "--disable-renderer-backgrounding",
        "--disable-backgrounding-occluded-windows",
        # Edge 默认关闭窗口后还会后台常驻，占着调试端口
        "--disable-background-mode",
        "--no-service-autorun",
    ]
    return subprocess.Popen(cmd)  # 不捕获输出，否则浏览器可能启动不了


def cdp_endpoint(port: int = 9222) -> str:
    return f"http://127.0.0.1:{port}"


def is_cdp_alive(port: int = 9222, timeout: float = 1.5) -> bool:
    """探测 9222 端口上有没有可连的浏览器。"""
    import urllib.request

    try:
        with urllib.request.urlopen(f"{cdp_endpoint(port)}/json/version", timeout=timeout):
            return True
    except Exception:
        return False


def stop_browser(port: int = 9222) -> bool:
    """关闭通过调试端口启动的浏览器。

    分两步：
      1. 通过 CDP 优雅关闭
      2. 如果进程还赖着（Edge 会后台常驻），按「命令行含该端口」精确 kill
    绝不按进程名杀，避免误伤你日常用的浏览器。
    """
    alive = is_cdp_alive(port)
    if alive:
        pw = sync_playwright().start()
        try:
            browser = pw.chromium.connect_over_cdp(cdp_endpoint(port))
            browser.close()  # CDP 下这会关掉浏览器，所以只在这里用
        except Exception:
            pass
        finally:
            pw.stop()

    if sys.platform == "win32":
        ps = (
            "Get-CimInstance Win32_Process | "
            "Where-Object { $_.CommandLine -like '*remote-debugging-port="
            f"{port}"
            "*' -and ($_.Name -eq 'msedge.exe' -or $_.Name -eq 'chrome.exe') } | "
            "ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"
        )
        try:
            subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps],
                capture_output=True,
                timeout=20,
            )
        except Exception:
            pass

    return alive


class CdpCollector:
    """连到已启动的浏览器，旁听指定接口的响应。

    用法：
        c = CdpCollector(port=9222, match="joblist.json")
        page = c.open(url)
        c.wait_for_data(timeout_s=20)
        jobs = c.collect_payloads()
    """

    def __init__(self, port: int = 9222, match: str = "joblist.json") -> None:
        self.port = port
        self.match = match
        self.captured: list[dict[str, Any]] = []
        self._seen: set[str] = set()

        self._pw = sync_playwright().start()
        try:
            self.browser = self._pw.chromium.connect_over_cdp(cdp_endpoint(port))
        except Exception as e:
            raise RuntimeError(
                f"连不上 CDP（端口 {port}）。先运行：job-scout browser\n原始错误：{e}"
            ) from e

        self.context = (
            self.browser.contexts[0] if self.browser.contexts else self.browser.new_context()
        )
        self.page: Page | None = None
        self.reused = False
        self.created = False  # 只有我们自己新建的标签才允许关闭

    def _find_page(self, keyword: str) -> Page | None:
        for p in self.context.pages:
            try:
                if p.is_closed():
                    continue
                if keyword in p.url:
                    return p
            except Exception:
                continue
        return None

    def _navigate(self, page: Page, url: str, timeout_ms: int = 60_000) -> None:
        """导航，并且确认真的到了目标页。

        Chrome 会把后台标签丢弃（discard），这时候 reload/goto 可能
        报 "Not attached to an active page"，或者导航完停在 about:blank。
        所以这里做两件事：失败重试一次 + 校验最终 URL。
        """
        last_err: Exception | None = None
        for attempt in (1, 2):
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
            except Exception as e:
                last_err = e
                page.wait_for_timeout(1000)
                continue

            if page.url != "about:blank":
                return
            # 落在了 about:blank，等一会儿再试一次
            page.wait_for_timeout(1500)
            if page.url != "about:blank":
                return

        raise RuntimeError(
            "页面停在 about:blank —— 目标标签可能被浏览器冻结了。"
            " 解决：关掉浏览器，重新双击 start_browser.bat，登录后停在职位搜索页再运行。"
            if last_err is None
            else f"导航失败：{last_err}"
        )

    def goto(self, url: str, timeout_ms: int = 60_000) -> None:
        """在当前页面里导航（带 about:blank 兜底）。"""
        if self.page is None:
            raise RuntimeError("还没有打开页面")
        self._navigate(self.page, url, timeout_ms)

    def attach(self, keyword: str = "zhipin.com/web/geek/jobs") -> Page:
        """附着到用户已经打开并滚好的页面：只挂监听，不导航、不新建。

        用于「页面已经在那儿了，我只想开始听」的场景。
        """
        page = self._find_page(keyword)
        if page is None:
            for p in self.context.pages:
                try:
                    if not p.is_closed() and p.url.startswith("http"):
                        page = p
                        break
                except Exception:
                    continue
        if page is None:
            raise RuntimeError("没有可附着的标签页，请先在浏览器里打开职位搜索页")

        self.page = page
        self.reused = True
        page.on("response", self._on_response)
        return page

    def wheel_scroll(self, clicks: int = 1, delta: int = 900, gap_s: float = 1.5) -> int:
        """用真实滚轮事件往下翻（比 scrollTo 更接近人手，触发懒加载更可靠）。"""
        if self.page is None:
            return 0
        before = len(self.captured)
        try:
            self.page.mouse.move(420, 420)
        except Exception:
            pass
        for _ in range(clicks):
            try:
                self.page.mouse.wheel(0, delta)
            except Exception:
                pass
            self._pump(gap_s)
        return len(self.captured) - before

    def open(self, url: str, reuse_keyword: str | None = "zhipin.com/web/geek/jobs") -> Page:
        """打开页面：永远优先复用你已有的标签，尽量不新建。

        实测教训：通过 CDP 新建的标签在当前浏览器实例里经常渲染不出来
        （白屏、title 为空、evaluate 返回 0）。复用用户已经打开的标签稳定得多。
        """
        page = self._find_page(reuse_keyword) if reuse_keyword else None

        # 没有匹配的搜索页，就退而求其次：用任意一个已存在的标签
        if page is None:
            for p in self.context.pages:
                try:
                    if not p.is_closed() and p.url.startswith("http"):
                        page = p
                        break
                except Exception:
                    continue

        if page is not None:
            try:
                page.on("response", self._on_response)
                self._navigate(page, url, timeout_ms=40_000)
                self.reused = True
                self.page = page
                return page
            except Exception:
                pass  # 复用失败，最后才考虑新建

        self.reused = False
        self.created = True
        self.page = self.context.new_page()
        self.page.on("response", self._on_response)
        self._navigate(self.page, url)
        return self.page

    def _on_response(self, response) -> None:
        """只旁听，不注入。页面自己请求什么，我们记什么。"""
        if self.match not in response.url:
            return
        try:
            data = response.json()
        except Exception:
            return
        key = response.url
        if key in self._seen:
            return
        self._seen.add(key)
        self.captured.append({"url": response.url, "data": data})

    def pump(self, seconds: float) -> None:
        """对外暴露的等待（保持事件循环运行）。"""
        self._pump(seconds)

    def _pump(self, seconds: float) -> None:
        """等待，但保持事件循环运行。

        关键坑：Playwright 同步 API 靠「把控制权交回 driver」来分发事件。
        直接 `time.sleep()` 会把线程卡住，response 回调永远不触发，
        看起来就像「一条数据都没抓到」。
        必须用 `page.wait_for_timeout()`，它在等待时仍处理事件。
        """
        if self.page is not None:
            try:
                self.page.wait_for_timeout(int(seconds * 1000))
                return
            except Exception:
                pass
        time.sleep(seconds)

    def wait_for_data(self, timeout_s: int = 20, poll_s: float = 1.0) -> bool:
        deadline = time.time() + timeout_s
        while time.time() < deadline:
            if self.captured:
                return True
            self._pump(poll_s)
        return bool(self.captured)

    # 把所有可滚动容器都推到底。BOSS 的列表不一定挂在 window 上，
    # 只滚 window 经常一条都加载不出来（踩过）。
    SCROLL_JS = """
    (() => {
      let moved = 0;
      const se = document.scrollingElement || document.documentElement;
      const before = se.scrollTop;
      se.scrollTop = se.scrollHeight;
      if (se.scrollTop !== before) moved++;
      document.querySelectorAll('*').forEach(el => {
        if (el.scrollHeight > el.clientHeight + 100 && el.clientHeight > 150) {
          const b = el.scrollTop;
          el.scrollTop = el.scrollHeight;
          if (el.scrollTop !== b) moved++;
        }
      });
      return moved;
    })()
    """

    def scroll_more(self, times: int = 1, gap_s: float = 3.0) -> int:
        """滚到底，触发页面自己的无限加载，继续旁听。返回新增响应数。"""
        if self.page is None:
            return 0
        before = len(self.captured)
        for _ in range(times):
            try:
                self.page.evaluate(self.SCROLL_JS)
            except Exception:
                pass
            self._pump(gap_s)
        return len(self.captured) - before

    def has_more(self) -> bool:
        """从接口响应里读 hasMore。没读到就当作还有。"""
        for item in self.captured:
            zp = (item.get("data") or {}).get("zpData") or {}
            if zp.get("hasMore") is False:
                return False
        return True

    def total_count(self) -> int | None:
        for item in self.captured:
            zp = (item.get("data") or {}).get("zpData") or {}
            if isinstance(zp.get("totalCount"), int):
                return zp["totalCount"]
        return None

    def payloads(self) -> list[dict[str, Any]]:
        return [c["data"] for c in self.captured]

    def body_text(self) -> str:
        if self.page is None:
            return ""
        try:
            return self.page.inner_text("body")
        except Exception:
            return ""

    def url(self) -> str:
        return self.page.url if self.page else ""

    def screenshot(self, path: str | Path) -> Path:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        if self.page:
            self.page.screenshot(path=str(p))
        return p

    def close(self) -> None:
        """断开连接。

        三个坑：
          1. 不能调 browser.close()——CDP 下会直接关掉用户浏览器
          2. 不能关最后一个标签——Chrome/Edge 会连浏览器一起退出
          3. 所以：标签不止一个时才关自己的标签，否则留着
        """
        try:
            if self.created and self.page is not None and not self.page.is_closed():
                if len(self.context.pages) > 1:
                    self.page.close()
        except Exception:
            pass
        self._pw.stop()


def dump_json(path: str | Path, data: Any) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return p
