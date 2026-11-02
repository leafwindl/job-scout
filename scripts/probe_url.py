"""打开任意 URL，看它渲染成什么样。用于排查空白页。

    uv run python scripts/probe_url.py https://www.zhipin.com/
"""

from __future__ import annotations

import sys

from job_scout.tools.cdp import CdpCollector


def main(url: str) -> None:
    col = CdpCollector(port=9222, match="__no_match__")
    try:
        col.open(url)
        col.page.wait_for_timeout(6000)
        print("url      :", col.url())
        print("title    :", col.page.title())
        print("html_len :", len(col.page.content()))
        body = col.body_text()
        print("body_len :", len(body))
        print("body_head:", body[:200].replace("\n", " "))
        shot = col.screenshot("data/raw/_probe_page.png")
        print("screenshot:", shot.resolve())
    finally:
        col.close()


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "https://www.zhipin.com/")
