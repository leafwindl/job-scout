"""命令行入口。

分三步走，对应里程碑：
  job-scout config       看配置（确认 YAML 改对了）
  job-scout probe        打开页面 → 你手动登录 → 存 HTML（M1）
  job-scout parse        解析已存的 HTML → 入库（M2）
"""

from __future__ import annotations

import json
import random
import sys
import time
import uuid
from pathlib import Path

# Windows 终端默认 GBK，Rich 输出 UTF-8 会乱码。
# 在导入 rich 之前把控制台和 stdio 都切成 UTF-8。
if sys.platform == "win32":
    try:
        import ctypes

        ctypes.windll.kernel32.SetConsoleOutputCP(65001)
        ctypes.windll.kernel32.SetConsoleCP(65001)
    except Exception:
        pass
    for _stream in (sys.stdout, sys.stderr):
        try:
            _stream.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
        except Exception:
            pass

import typer
from rich.console import Console
from rich.table import Table

from job_scout.config import load_search_config, settings
from job_scout.constants import CITY_CODES
from job_scout.dashboard import open_dashboard
from job_scout.dashboard import render as render_dashboard
from job_scout.models import SearchQuery
from job_scout.server import serve as run_server
from job_scout.server import to_posting
from job_scout.sources.boss import BossAdapter, RiskControlError
from job_scout.sources.shixiseng import ShixisengAdapter
from job_scout.storage import Storage
from job_scout.tools.browser import PlaywrightDriver
from job_scout.tools.cdp import (
    CdpCollector,
    dump_json,
    is_cdp_alive,
    launch_browser,
    stop_browser,
)

app = typer.Typer(add_completion=False, help="招聘信息采集与分析 Agent")
console = Console()

ADAPTERS = {"boss": BossAdapter, "shixiseng": ShixisengAdapter}


def get_adapter(name: str):
    cls = ADAPTERS.get(name)
    if cls is None:
        raise typer.BadParameter(f"未知站点：{name}，可选：{list(ADAPTERS)}")
    return cls()


@app.command()
def config() -> None:
    """打印当前搜索配置，确认 YAML 已生效。"""
    cfg = load_search_config()
    table = Table(title="搜索配置", show_lines=False)
    table.add_column("关键词", style="cyan")
    table.add_column("城市", style="green")
    table.add_column("最多页数", justify="right")
    for q in cfg.queries:
        table.add_row(q.keyword, q.city, str(q.max_pages))
    console.print(table)
    console.print(
        f"[dim]限速：{cfg.limits.page_delay_ms}ms/页，"
        f"detail 上限 {cfg.limits.max_detail_fetch} 条，"
        f"headless={cfg.limits.headless}[/]"
    )


@app.command()
def probe(
    site: str = typer.Option("boss", help="站点：boss / shixiseng"),
    keyword: str = typer.Option("Agent开发", help="搜索关键词"),
    city: str = typer.Option("广州", help="城市"),
    out: str = typer.Option("", help="HTML 保存路径，留空自动生成"),
    channel: str = typer.Option("", help="浏览器渠道：msedge / chrome / 留空读配置"),
    warmup: bool = typer.Option(True, help="先访问首页热身，降低风控概率"),
) -> None:
    """打开搜索页，等你手动登录 / 过验证，然后保存页面 HTML。"""
    adapter = get_adapter(site)
    cfg = load_search_config()
    query = SearchQuery(keyword=keyword, city=city)
    url = adapter.search_url(query)

    out_path = Path(out) if out else Path("data/raw") / f"{site}_{keyword}.html"
    use_channel = channel or settings.browser_channel or None

    console.print(f"[cyan]站点[/] {site}   [cyan]城市[/] {city}   [cyan]关键词[/] {keyword}")
    console.print(f"[cyan]渠道[/] {use_channel or '自带 Chromium'}")
    console.print(f"[cyan]地址[/] {url}")

    drv = PlaywrightDriver(
        profile_dir=settings.browser_profile_dir,
        headless=cfg.limits.headless,
        channel=use_channel,
    )
    try:
        # 步骤 1：打开首页，停住等用户处理验证和登录
        # 注意：这里不会自动往下走，必须用户按回车。
        if warmup:
            console.print("\n[bold cyan]步骤 1/2[/] 打开首页，由你处理验证和登录")
            drv.open("https://www.zhipin.com/")
            _report_page_state(drv)
            console.print("[yellow]  · 看到「安全验证」，就点按钮把它过掉[/]")
            console.print("[yellow]  · 然后登录你的账号[/]")
            input("\n>>> 登录完成后按回车，我再跳去搜索页 ")

        # 步骤 2：跳到搜索页，再停一次
        console.print("\n[bold cyan]步骤 2/2[/] 打开搜索页")
        drv.open(url)
        _report_page_state(drv)
        console.print("[yellow]  · 等岗位列表显示出来（没出来就手动刷新或往下滚）[/]")
        input("\n>>> 列表出来后按回车，我来保存 ")

        text = drv.body_text()
        cards = drv.count(adapter.SEL_CARD)
        console.print(f"\n[dim]页面状态：正文 {len(text)} 字符，岗位卡片 {cards} 个[/]")

        if "安全验证" in text or "异常访问" in text:
            console.print("[red]⚠ 还在安全验证页[/] 这次存下来意义不大，建议重跑")
            console.print("[red]  也可能是这个 profile 被标记了，换个目录试试：[/]")
            console.print("[red]  job-scout probe --out data/raw/x.html（先删 .playwright/profile）[/]")
        elif cards == 0:
            console.print("[yellow]⚠ 没识别到岗位卡片，可能站点改版或还没加载完[/]")
            console.print("[yellow]  先存下来，我看过 HTML 再改选择器。[/]")

        saved = drv.save_html(out_path)
        shot = drv.screenshot("data/raw/_last_page.png")
        console.print(f"[green]✓ HTML[/] {saved.resolve()}  ({saved.stat().st_size / 1024:.0f} KB)")
        console.print(f"[green]✓ 截图[/] {shot.resolve()}")
        console.print("\n下一步：")
        console.print(f"  [dim]job-scout parse \"{saved}\" --site {site}[/]")
    finally:
        drv.close()


def _report_page_state(drv: PlaywrightDriver) -> None:
    """把当前页面处在什么状态翻译成人话。"""
    info = drv.page_info()
    text = drv.body_text()
    body_len = len(text)

    console.print(f"\n[dim]当前页：{info['url']}[/]")
    console.print(f"[dim]标题：{info['title']}[/]")
    console.print(f"[dim]正文长度：{body_len} 字符[/]")

    if "安全验证" in text or "异常访问" in text:
        console.print("[red]→ 命中安全验证页（风控）[/]，需要你手动点按钮过掉")
    elif body_len < 200:
        console.print("[yellow]→ 页面几乎是空的[/]，可能是加载没完成，先别急")
    else:
        console.print(f"[green]→ 页面已渲染[/] {text.strip()[:80]!r}")

    if body_len < 200:
        shot = drv.screenshot("data/raw/_debug_blank.png")
        console.print(f"[dim]已截图：{shot.resolve()}[/]")


@app.command()
def parse(
    html_file: str = typer.Argument(..., help="probe 保存下来的 HTML 路径"),
    site: str = typer.Option("boss", help="按哪个适配器解析"),
    save: bool = typer.Option(True, help="是否写入数据库"),
) -> None:
    """解析 HTML，抽取岗位，可选入库。"""
    adapter = get_adapter(site)
    raw = Path(html_file).read_text(encoding="utf-8")

    try:
        postings = adapter.parse_list(raw)
    except ValueError as e:
        console.print(f"[red]解析失败[/]\n{e}")
        raise typer.Exit(code=1)

    console.print(f"[green]解析到 {len(postings)} 条岗位[/]")

    table = Table(show_lines=False)
    table.add_column("#", justify="right", style="dim")
    table.add_column("岗位", style="cyan", max_width=28)
    table.add_column("公司", max_width=20)
    table.add_column("薪资", justify="right")
    table.add_column("城市")
    table.add_column("标签", max_width=30)
    for i, p in enumerate(postings[:20], 1):
        table.add_row(
            str(i), p.title, p.company, p.salary_raw or "-",
            f"{p.city or '-'} {p.district or ''}".strip(),
            ",".join(p.skills[:4]),
        )
    console.print(table)
    if len(postings) > 20:
        console.print(f"[dim]…仅显示前 20 条，共 {len(postings)} 条[/]")

    if save:
        store = Storage(settings.db_path)
        for p in postings:
            store.upsert(p)
        console.print(f"[green]✓ 已入库[/] {settings.db_path}，当前共 {store.count()} 条")
        store.close()


@app.command()
def browser(
    channel: str = typer.Option("msedge", help="msedge / chrome"),
    profile: str = typer.Option(".playwright/boss-profile", help="独立 profile 目录"),
    port: int = typer.Option(9222, help="远程调试端口"),
) -> None:
    """启动一个带调试端口的独立浏览器（和你日常浏览器互不影响）。

    ⚠ 更推荐直接双击项目根目录的 `start_browser.bat`：
      由你自己启动浏览器、自己登录，程序只负责连上去读。
    """
    if is_cdp_alive(port):
        console.print(f"[green]端口 {port} 上已经有浏览器在跑[/]，直接 collect 即可")
        return

    proc = launch_browser(channel, profile, port)
    console.print(f"[green]✓ 已启动 {channel}[/]  PID={proc.pid}")

    for _ in range(30):
        if is_cdp_alive(port):
            break
        time.sleep(0.5)

    alive = is_cdp_alive(port)
    console.print(f"[dim]调试端口 {port}：{'就绪' if alive else '还没起来，等一下再看'}[/]")
    console.print(f"[dim]profile：{Path(profile).resolve()}[/]")
    console.print()
    console.print("[yellow]请在这个浏览器窗口里登录 BOSS直聘[/]")
    console.print("[yellow]登录一次就行，登录态存在独立 profile 里[/]")
    console.print("\n登录好之后运行：")
    console.print("  [dim]job-scout collect --keyword Agent开发 --city 广州[/]")


@app.command()
def dashboard(
    open_browser: bool = typer.Option(True, "--open/--no-open", help="生成后自动用浏览器打开"),
) -> None:
    """把已采集的岗位渲染成可视化看板（单文件 HTML，离线可用）。"""
    db = Path(settings.db_path)
    if not db.exists():
        console.print("[red]数据库不存在，先跑一次 collect。[/]")
        raise typer.Exit(code=1)

    path = render_dashboard(db)
    size_mb = path.stat().st_size / 1024 / 1024
    console.print(f"[green]✓ 看板已生成[/] {path.resolve()}  ({size_mb:.1f} MB)")

    if open_browser:
        open_dashboard(path)
        console.print("[dim]已在浏览器打开[/]")


@app.command("rag-eval")
def rag_eval(
    only_intern: bool = typer.Option(True, help="只评实习岗"),
    per_kind: int = typer.Option(12, help="每类评测问题数"),
    rebuild: bool = typer.Option(False, "--rebuild", help="强制重建向量索引"),
    rerank: bool = typer.Option(
        False,
        "--rerank/--no-rerank",
        help="启用 LLM 重排（很慢，一次调用 ~80s，且实测负优化）",
    ),
) -> None:
    """检索评测：BM25 / 向量 / RRF 融合 / 自适应路由。"""
    from job_scout.rag.bm25 import BM25Retriever
    from job_scout.rag.corpus import load_docs
    from job_scout.rag.evaluate import build_eval_set, evaluate
    from job_scout.rag.hybrid import AdaptiveRerankRetriever, HybridRetriever

    docs = load_docs(settings.db_path, only_intern=only_intern)
    if not docs:
        console.print("[red]没有可用文档，先采集并抓 JD[/]")
        raise typer.Exit(code=1)

    items = build_eval_set(docs, per_kind=per_kind)
    console.print(f"[cyan]语料[/] {len(docs)} 篇   [cyan]评测集[/] {len(items)} 条")

    configs: list[tuple[str, object]] = [("BM25", BM25Retriever(docs, field="text"))]
    adaptive = None
    reranked = None
    rerank_impl = None

    try:
        from job_scout.rag.embedder import Embedder
        from job_scout.rag.vector import VectorRetriever

        console.print("[dim]准备向量索引（首次会下载模型并编码，稍等）…[/]")
        embedder = Embedder()
        vector = VectorRetriever.build(docs, embedder, force=rebuild)
        hybrid = HybridRetriever(BM25Retriever(docs, field="text"), vector)
        adaptive = AdaptiveRerankRetriever(hybrid)
        configs += [("向量", vector), ("RRF 融合", hybrid)]

        # 第四组：重排。默认关闭——LLM listwise 排序一次要 80 秒且是负优化
        if rerank:
            rerank_impl = None
            rerank_label = ""
            try:
                from job_scout.rag.reranker import CrossEncoderReranker, model_available

                if model_available():
                    rerank_impl = CrossEncoderReranker()
                    rerank_label = "+自适应重排(CE)"
            except Exception as e:  # noqa: BLE001
                console.print(f"[dim]cross-encoder 不可用：{type(e).__name__}[/]")

            if rerank_impl is None:
                from job_scout.rag.llm import get_llm

                llm = get_llm()
                if llm is not None:
                    from job_scout.rag.llm_reranker import LLMReranker

                    rerank_impl = LLMReranker(llm)
                    rerank_label = "+自适应重排(LLM)"

            if rerank_impl is not None:
                reranked = AdaptiveRerankRetriever(hybrid, reranker=rerank_impl)
                configs.append((rerank_label, reranked))
                console.print(f"[dim]重排方式：{rerank_label}[/]")
            else:
                console.print("[yellow]没有可用的重排器，跳过第四组[/]")
    except Exception as e:
        console.print(f"[yellow]向量检索不可用，仅跑 BM25：{type(e).__name__}: {e}[/]")

    table = Table(title="检索配置对比")
    table.add_column("配置")
    table.add_column("Recall@1", justify="right")
    table.add_column("Recall@5", justify="right")
    table.add_column("Recall@10", justify="right")
    table.add_column("Precision@10", justify="right")
    table.add_column("MRR", justify="right")

    results = {}
    for label, retriever in configs:
        res = evaluate(retriever, items)  # type: ignore[arg-type]
        results[label] = res
        o = res["overall"]
        table.add_row(
            label,
            f"{o['recall@1']:.3f}",
            f"{o['recall@5']:.3f}",
            f"{o['recall@10']:.3f}",
            f"{o['precision@10']:.3f}",
            f"{o['mrr']:.3f}",
        )
    console.print(table)
    console.print(
        "[dim]技能类答案多（可达上百条），看 Precision@10；"
        "公司/区域类答案少，看 Recall@10 与 MRR[/]"
    )

    if reranked is not None:
        s = reranked.stats
        total = s["reranked"] + s["skipped"]
        console.print(
            f"[dim]自适应重排：{s['reranked']}/{total} 条触发重排，"
            f"{s['skipped']} 条因分差大跳过（阈值 {reranked.gap_threshold}）[/]"
        )
        errs = getattr(rerank_impl, "errors", 0)
        if errs:
            console.print(f"[yellow]重排调用失败 {errs} 次（已回退原顺序）[/]")
    elif adaptive is not None:
        # 没有重排模型时只统计分差分布
        evaluate(adaptive, items)
        gaps = sorted(adaptive.gaps)
        n = len(gaps)
        if n:
            by_th = ", ".join(
                f"{th}: {sum(1 for g in gaps if g > th) / n:.0%}"
                for th in (0.02, 0.05, 0.1)
            )
            console.print(
                f"[dim]融合分差（相对）：median {gaps[n // 2]:.3f}｜"
                f"按阈值可跳过重排比例 {by_th}[/]"
            )
        console.print(
            "[yellow]自适应重排未接入 reranker，本轮只统计分差分布；"
            "接入后按阈值 0.05 预计跳过约两成重排调用[/]"
        )

    best = results.get("RRF 融合") or results["BM25"]
    t2 = Table(title="按查询类型（融合配置）")
    t2.add_column("类型")
    t2.add_column("数量", justify="right")
    t2.add_column("Recall@10", justify="right")
    t2.add_column("Precision@10", justify="right")
    t2.add_column("MRR", justify="right")
    for kind, v in best["by_kind"].items():
        t2.add_row(
            kind,
            str(v["n"]),
            f"{v['recall@10']:.3f}",
            f"{v['precision@10']:.3f}",
            f"{v['mrr']:.3f}",
        )
    console.print(t2)

    bad = [r for r in best["rows"] if r["recall"][10] == 0][:5]
    if bad:
        console.print("\n[dim]完全没召回的查询：[/]")
        for r in bad:
            console.print(f"  [yellow]{r['query']}[/]  gold={r['gold']}")


def _port_in_use(port: int) -> bool:
    import socket

    s = socket.socket()
    try:
        s.bind(("127.0.0.1", port))
        return False
    except OSError:
        return True
    finally:
        s.close()


def _get_json(url: str, timeout: float = 3.0) -> dict:
    import urllib.request

    with urllib.request.urlopen(url, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


@app.command()
def auto(
    keyword: str = typer.Option("Agent 实习", help="搜索关键词"),
    city: str = typer.Option("广州", help="城市"),
    port: int = typer.Option(8766, help="本地接收端口"),
    timeout_min: int = typer.Option(40, help="最长等待分钟数"),
    open_browser: bool = typer.Option(True, "--open/--no-open", help="自动打开浏览器"),
) -> None:
    """一键采集：起服务 → 打开浏览器 → 自动滚动抓 JD → 生成看板。

    前置条件：浏览器已安装油猴脚本，且已登录 BOSS 直聘。
    脚本收到 ?jobscout=auto 后会自动开始，抓完 JD 会回报，本命令随即出看板。
    """
    import threading
    import time
    import webbrowser
    from urllib.parse import quote

    code = CITY_CODES.get(city)
    if code is None:
        console.print(f"[red]不认识的城市：{city}[/]，可选：{'、'.join(CITY_CODES)}")
        raise typer.Exit(code=1)

    if _port_in_use(port):
        console.print(f"[dim]端口 {port} 已有服务在跑，直接复用[/]")
    else:
        console.print(f"[dim]启动本地接收服务 :{port} …[/]")
        threading.Thread(target=run_server, args=(port,), daemon=True).start()
        time.sleep(1.2)

    url = (
        f"https://www.zhipin.com/web/geek/job"
        f"?query={quote(keyword)}&city={code}&jobscout=auto"
    )

    console.print()
    console.print(f"[cyan]关键词[/] {keyword}   [cyan]城市[/] {city}")
    console.print(f"[cyan]采集地址[/] {url}")
    console.print("[dim]浏览器里首次可能需要登录；登录后脚本会自动接上。[/]")
    console.print("[dim]按 Ctrl+C 可随时中断。[/]")
    console.print()

    if open_browser:
        webbrowser.open(url)
    else:
        console.print("[yellow]请手动打开上面的地址[/]")

    started = time.time()
    deadline = started + timeout_min * 60
    last_total = -1
    stable_since = 0.0
    done = False

    try:
        while time.time() < deadline:
            time.sleep(5)
            try:
                h = _get_json(f"http://127.0.0.1:{port}/health")
            except Exception:
                console.print("[dim]等待服务就绪…[/]")
                continue

            total = int(h.get("total") or 0)
            pending = int(h.get("jd_pending") or 0)
            done_at = float(h.get("auto_done_at") or 0)
            elapsed = int(time.time() - started)

            if total != last_total:
                last_total = total
                stable_since = time.time()

            clock = time.strftime("%H:%M:%S")
            console.print(
                f"[dim]{clock}[/] 岗位 [cyan]{total}[/]  待抓 JD [cyan]{pending}[/]  "
                f"已用 {elapsed // 60:02d}:{elapsed % 60:02d}"
            )

            # 只认「本次启动之后」的完成信号，上次的残留不算
            if done_at >= started:
                done = True
                break
            # 兜底：岗位数稳定 3 分钟且没有待抓正文，视为结束
            if total > 0 and pending == 0 and time.time() - stable_since > 180:
                done = True
                break
    except KeyboardInterrupt:
        console.print("\n[yellow]已中断[/]")

    if not done:
        console.print(
            f"\n[yellow]等待超时（{timeout_min} 分钟）[/]，"
            "可能是未登录、被风控，或脚本没更新到 0.8.0。"
        )

    # 留一点时间给脚本把最后一批推送完
    time.sleep(3)

    store = Storage(settings.db_path)
    total = store.count()
    with_jd = store.count_pending_jd()
    store.close()
    console.print(f"\n[green]库内共 {total} 条岗位，其中 {total - with_jd} 条有 JD 正文[/]")

    if total > 0:
        path = render_dashboard(Path(settings.db_path))
        console.print(f"[green]✓ 看板已生成[/] {path.resolve()}")
        if open_browser:
            open_dashboard(path)
            console.print("[dim]已在浏览器打开看板[/]")


@app.command("purge-non-intern")
def purge_non_intern(
    yes: bool = typer.Option(False, "--yes", help="确认删除（默认只统计不删）"),
) -> None:
    """清理混进来的全职岗位（标题不含「实习」）。

    采集端已经改成只收 jobType=4 的实习岗，这个命令处理历史数据。
    """
    import shutil
    import time

    store = Storage(settings.db_path)
    total = store.count()
    non_intern = store.count_non_intern()

    if non_intern == 0:
        store.close()
        console.print("[green]没有非实习岗位，不用清理[/]")
        return

    console.print(f"库内共 {total} 条，其中 [yellow]{non_intern}[/] 条不是实习岗")
    if not yes:
        store.close()
        console.print("[dim]确认要删就加 --yes（会先备份数据库）[/]")
        return

    backup = Path(settings.db_path).with_name(
        f"job_scout_backup_{time.strftime('%Y%m%d_%H%M%S')}.db"
    )
    store.close()
    shutil.copy2(settings.db_path, backup)
    console.print(f"[dim]已备份到 {backup}[/]")

    store = Storage(settings.db_path)
    deleted = store.delete_non_intern()
    left = store.count()
    store.close()

    console.print(f"[green]✓ 删除 {deleted} 条，剩余 {left} 条[/]")


@app.command()
def daily(
    keyword: str = typer.Option("Agent 实习", help="搜索关键词"),
    city: str = typer.Option("广州", help="城市"),
    port: int = typer.Option(8766, help="采集接收端口"),
    stale_days: int = typer.Option(
        7, help="超过几天没出现算停招（默认 7，太短会误伤没跑的查询）"
    ),
    timeout_min: int = typer.Option(70, help="最长等待分钟"),
    open_browser: bool = typer.Option(True, "--open/--no-open", help="自动打开浏览器"),
    make_dashboard: bool = typer.Option(True, "--dashboard/--no-dashboard"),
) -> None:
    """每日增量更新：采列表 → 抓 JD → 标记停招 → 出日报。

    只抓本轮新增 / 缺 JD 的岗位，不会重复爬，一小时左右能跑完。
    适合挂到 Windows 计划任务里每天自动跑。
    """
    import threading
    import time
    import webbrowser
    from datetime import datetime
    from urllib.parse import quote

    code = CITY_CODES.get(city)
    if code is None:
        console.print(f"[red]不认识的城市：{city}[/]，可选：{'、'.join(CITY_CODES)}")
        raise typer.Exit(code=1)

    started_iso = datetime.now().isoformat(timespec="seconds")
    started_ts = time.time()

    if _port_in_use(port):
        console.print(f"[dim]端口 {port} 已有服务在跑，复用[/]")
    else:
        threading.Thread(target=run_server, args=(port,), daemon=True).start()
        time.sleep(1.2)

    url = (
        f"https://www.zhipin.com/web/geek/job"
        f"?query={quote(keyword)}&city={code}&jobscout=auto"
    )

    console.print()
    console.print(f"[cyan]每日更新[/] {datetime.now():%Y-%m-%d %H:%M}")
    console.print(f"[cyan]关键词[/] {keyword}   [cyan]城市[/] {city}")
    console.print(f"[cyan]地址[/] {url}")
    console.print("[dim]滚动采列表 → 自动切导航模式抓 JD → 回报完成。Ctrl+C 可中断。[/]")
    console.print()

    if open_browser:
        webbrowser.open(url)
    else:
        console.print("[yellow]请手动打开上面的地址[/]")

    deadline = started_ts + timeout_min * 60
    done = False
    last_total = -1

    try:
        while time.time() < deadline:
            time.sleep(15)
            try:
                h = _get_json(f"http://127.0.0.1:{port}/health")
            except Exception:
                continue
            total = int(h.get("total") or 0)
            pending = int(h.get("jd_pending") or 0)
            done_at = float(h.get("auto_done_at") or 0)

            if total != last_total:
                last_total = total
            clock = time.strftime("%H:%M:%S")
            console.print(f"[dim]{clock}[/] 岗位 {total}｜待抓 JD {pending}")

            if done_at >= started_ts:
                done = True
                break
    except KeyboardInterrupt:
        console.print("\n[yellow]已中断，仍会标记停招并出日报[/]")

    time.sleep(2)

    store = Storage(settings.db_path)
    stale = store.mark_stale(stale_days)
    stats = store.daily_stats(started_iso)
    store.close()

    console.print()
    console.print("[bold]═══ 今日日报 ═══[/]")
    console.print(f"  新增岗位    [cyan]{stats['new_today']}[/]")
    console.print(f"  标记停招    [yellow]{stale}[/] 条（{stale_days} 天没出现）")
    console.print(f"  在架岗位    {stats['active']}")
    console.print(f"  有 JD 正文  [green]{stats['with_jd']}[/]")
    if not done:
        console.print(f"  [yellow]未收到完成信号，可能超时（{timeout_min} 分钟）[/]")

    if make_dashboard and stats["active"] > 0:
        path = render_dashboard(Path(settings.db_path))
        console.print(f"\n[green]✓ 看板已生成[/] {path.resolve()}")
        if open_browser:
            open_dashboard(path)
            console.print("[dim]已在浏览器打开看板[/]")


@app.command("purge-irrelevant")
def purge_irrelevant(
    yes: bool = typer.Option(False, "--yes", help="确认删除（默认只统计）"),
    show: int = typer.Option(15, help="抽样展示多少条将被删除"),
) -> None:
    """删除与 AI/Agent 无关的岗位（分类落到「通用/后端底子」的）。

    采集端已经加了相关性过滤，这个命令处理历史数据。
    """
    import shutil
    import time

    from job_scout.classify import FALLBACK, classify
    from job_scout.constants import title_relevant

    store = Storage(settings.db_path)
    rows = store.conn.execute(
        "SELECT job_id, title, company, skills, description FROM postings WHERE is_active = 1"
    ).fetchall()

    drop: list[tuple[str, str, str]] = []
    for r in rows:
        title = r["title"] or ""
        # 标题沾 AI 关键词的一律保留，避免误杀（没抓到 JD 时分类不可靠）
        if title_relevant(title):
            continue

        try:
            skills = json.loads(r["skills"] or "[]")
        except Exception:
            skills = []
        text = (r["description"] or "") or f"{title} {' '.join(skills)}"
        cat, _ = classify(text)
        if cat == FALLBACK:
            drop.append((r["job_id"], title, r["company"] or ""))

    kept = len(rows) - len(drop)
    console.print(f"在架 {len(rows)} 条，其中 [yellow]{len(drop)}[/] 条与 AI/Agent 无关，保留 {kept} 条")

    if drop and show:
        console.print("\n[dim]将要删除的样例：[/]")
        for _, title, company in drop[:show]:
            console.print(f"  [dim]{title} ｜ {company}[/]")

    if not drop:
        store.close()
        return

    if not yes:
        store.close()
        console.print("\n[dim]确认要删就加 --yes（会先备份数据库）[/]")
        return

    backup = Path(settings.db_path).with_name(
        f"job_scout_backup_{time.strftime('%Y%m%d_%H%M%S')}.db"
    )
    store.close()
    shutil.copy2(settings.db_path, backup)
    console.print(f"[dim]已备份到 {backup}[/]")

    store = Storage(settings.db_path)
    n = 0
    for jid, _, _ in drop:
        cur = store.conn.execute("DELETE FROM postings WHERE job_id = ?", (jid,))
        n += cur.rowcount
    store.conn.commit()
    left = store.count()
    store.close()

    console.print(f"[green]✓ 删除 {n} 条，剩余 {left} 条[/]")


@app.command("backfill-relevance")
def backfill_relevance() -> None:
    """给历史数据补 is_relevant 标记（按标题判断是否 AI/Agent 相关）。"""
    store = Storage(settings.db_path)
    rel, irr = store.backfill_relevance()
    pending = store.count_pending_jd()
    store.close()

    console.print(f"[green]✓ 已标记[/] 相关 {rel} 条，无关 {irr} 条")
    console.print(f"[dim]接下来 /pending 只会返回相关的待抓岗位：当前 {pending} 条[/]")


@app.command()
def cleanup(
    yes: bool = typer.Option(False, "--yes", help="确认删除（默认只看统计）"),
    keep_inactive: bool = typer.Option(
        False, "--keep-inactive", help="保留已停招的岗位（默认也清掉）"
    ),
) -> None:
    """清理数据库：只保留「实习 + AI/Agent 相关」的岗位。

    删除范围：标题不含「实习」的、或标题判为无关的（销售/助教/运营…）。
    默认连带清掉已停招的，加 --keep-inactive 可以留。
    """
    import shutil
    import time

    store = Storage(settings.db_path)
    total = store.count()

    where = "(title NOT LIKE '%实习%' OR is_relevant = 0)"
    if not keep_inactive:
        where = f"({where} OR is_active = 0)"

    drop = store.conn.execute(f"SELECT COUNT(*) FROM postings WHERE {where}").fetchone()[0]
    keep = total - drop

    console.print(f"总计 [cyan]{total}[/] 条")
    console.print(f"  保留  [green]{keep}[/] 条（实习 + 相关）")
    console.print(f"  删除  [yellow]{drop}[/] 条")

    if drop == 0:
        store.close()
        console.print("\n[green]已经很干净了，不用清理[/]")
        return

    # 预览保留下来的是什么
    preview = store.conn.execute(
        f"SELECT title FROM postings WHERE NOT {where} ORDER BY last_seen DESC LIMIT 6"
    ).fetchall()
    console.print("\n[dim]保留样例：[/]")
    for r in preview:
        console.print(f"  [dim]{r['title']}[/]")

    if not yes:
        store.close()
        console.print("\n[dim]确认要删就加 --yes（会自动备份数据库）[/]")
        return

    backup = Path(settings.db_path).with_name(
        f"job_scout_backup_{time.strftime('%Y%m%d_%H%M%S')}.db"
    )
    store.close()
    shutil.copy2(settings.db_path, backup)
    console.print(f"[dim]已备份到 {backup}[/]")

    store = Storage(settings.db_path)
    cur = store.conn.execute(f"DELETE FROM postings WHERE {where}")
    deleted = cur.rowcount
    store.conn.commit()
    left = store.count()
    store.conn.execute("VACUUM")
    store.close()

    console.print(f"[green]✓ 删除 {deleted} 条，剩余 {left} 条[/]")
    console.print("[dim]语料变了，建议重建向量索引：job-scout rag-eval --rebuild[/]")


@app.command()
def serve(port: int = typer.Option(8766, help="本地接收端口")) -> None:
    """启动本地接收服务，供油猴脚本推送数据。

    只监听 127.0.0.1，不对外暴露。
    """
    run_server(port)


@app.command(name="import")
def import_json(
    path: str = typer.Argument(..., help="油猴脚本导出的 JSON 文件"),
) -> None:
    """导入油猴脚本导出的 JSON（本地服务没开时的备用方案）。"""
    p = Path(path)
    if not p.exists():
        console.print(f"[red]文件不存在：{p}[/]")
        raise typer.Exit(code=1)

    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:
        console.print(f"[red]读取失败：{e}[/]")
        raise typer.Exit(code=1) from None

    jobs = data.get("jobs") if isinstance(data, dict) else data
    if not isinstance(jobs, list):
        console.print("[red]格式不对，应该是 {\"jobs\": [...]}[/]")
        raise typer.Exit(code=1)

    store = Storage(settings.db_path)
    new = 0
    for item in jobs:
        posting = to_posting(item)
        if posting is None:
            continue
        if store.upsert(posting):
            new += 1
    total = store.count()
    store.close()

    console.print(f"[green]✓ 导入完成[/] 收到 {len(jobs)} 条，新增 {new} 条，库内共 {total} 条")


@app.command()
def stop(port: int = typer.Option(9222, help="远程调试端口")) -> None:
    """关闭通过调试端口启动的浏览器（不影响你日常用的浏览器）。"""
    if stop_browser(port):
        console.print(f"[green]✓ 已关闭端口 {port} 上的浏览器[/]")
    else:
        console.print(f"[dim]端口 {port} 上没有运行中的浏览器[/]")


@app.command()
def collect(
    keyword: str = typer.Option("Agent开发", help="搜索关键词"),
    city: str = typer.Option("广州", help="城市"),
    port: int = typer.Option(9222, help="远程调试端口"),
    pages: int = typer.Option(20, help="最多翻页轮数（每页约 15 条）"),
    wait_s: int = typer.Option(40, help="首次等待接口响应的秒数"),
    save: bool = typer.Option(True, help="是否入库"),
    all_queries: bool = typer.Option(
        False, "--all", help="按 configs/search.yaml 跑全部查询"
    ),
) -> None:
    """连接已启动的浏览器，旁听页面自身请求采集岗位。

    会一直滚动翻页，直到接口返回 hasMore=false 或达到 --pages 上限。
    """
    if not is_cdp_alive(port):
        console.print(f"[red]端口 {port} 上没有浏览器，先把浏览器打开：[/]")
        console.print("  [dim]双击 start_browser.bat[/]")
        raise typer.Exit(code=1)

    if all_queries:
        cfg = load_search_config()
        targets = [(q.keyword, q.city, q.max_pages) for q in cfg.queries]
        if not targets:
            console.print("[red]configs/search.yaml 里没有 queries[/]")
            raise typer.Exit(code=1)
    else:
        targets = [(keyword, city, pages)]

    total_new = 0
    total_upd = 0
    failed = 0

    for idx, (kw, ct, max_pages) in enumerate(targets, 1):
        console.print(f"\n[bold cyan]===== {idx}/{len(targets)}  {kw} @ {ct} =====[/]")
        stats = _collect_one(kw, ct, port, pages if not all_queries else max_pages, wait_s, save)
        total_new += stats["new"]
        total_upd += stats["updated"]
        if stats["status"] != "ok":
            failed += 1

        if idx < len(targets):
            delay = random.uniform(3, 8)
            console.print(f"[dim]  停 {delay:.1f}s 再跑下一个…[/]")
            time.sleep(delay)

    console.print(
        f"\n[green]✓ 全部完成[/]  新增 {total_new} 条，更新 {total_upd} 条"
        + (f"，失败 {failed} 个查询" if failed else "")
    )


def _collect_one(
    keyword: str, city: str, port: int, max_pages: int, wait_s: int, save: bool
) -> dict:
    """跑一个关键词 + 城市。返回统计。"""
    adapter = BossAdapter()
    url = adapter.search_url(SearchQuery(keyword=keyword, city=city))
    console.print(f"[cyan]地址[/] {url}")

    try:
        col = CdpCollector(port=port, match="joblist.json")
    except Exception as e:
        console.print(f"[red]连不上浏览器：{e}[/]")
        return {"new": 0, "updated": 0, "status": "no_browser"}

    run_id = time.strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:6]
    store = Storage(settings.db_path) if save else None
    if store:
        store.start_run(run_id, keyword, city)
        console.print(f"[dim]run_id: {run_id}[/]")

    new_count = 0
    upd_count = 0
    captured = 0
    pages_done = 0
    status = "ok"

    try:
        try:
            col.open(url)
        except Exception as e:
            console.print(f"[red]打不开页面：{e}[/]")
            console.print(
                "[dim]建议：关掉浏览器 → 重新双击 start_browser.bat → "
                "登录后停在职位搜索页 → 再运行。[/]"
            )
            status = "open_failed"
            return {"new": 0, "updated": 0, "status": status}

        console.print(
            f"[dim]{'复用搜索页' if col.reused else '新开标签'}，等待接口（最多 {wait_s}s）…[/]"
        )

        ok = col.wait_for_data(timeout_s=wait_s)
        if not ok:
            text = col.body_text()
            if "安全验证" in text:
                console.print("[red]→ 命中安全验证页[/] 请在浏览器里手动点按钮过掉")
            console.print("[yellow]暂未捕获到搜索接口[/]")

            if sys.stdin.isatty():
                input("\n>>> 在浏览器里登录 / 过验证后按回车，我重试 ")
                try:
                    col.goto(url)
                    ok = col.wait_for_data(timeout_s=30)
                except Exception as e:
                    console.print(f"[red]重试失败：{e}[/]")

            if not ok:
                shot = col.screenshot("data/raw/_cdp_fail.png")
                console.print(f"[red]仍然没有数据[/] 截图：{shot.resolve()}")
                status = "no_data"
                return {"new": 0, "updated": 0, "status": status}

        total = col.total_count()
        console.print(
            f"[green]✓ 首个响应到达[/]  接口报告总量约 {total if total else '未知'} 条，开始翻页"
        )

        # ---- 翻页：滚到底，直到 hasMore=false 或连续两轮没新增 ----
        idle = 0
        for i in range(max_pages):
            added = col.scroll_more(times=1, gap_s=3.0)
            pages_done += 1
            console.print(f"[dim]  第 {i + 1} 轮，新增响应 {added}，累计 {len(col.captured)}[/]")
            if added == 0:
                idle += 1
                if idle >= 2:
                    console.print("[dim]  连续两轮没有新数据，停止翻页[/]")
                    break
            else:
                idle = 0
            if not col.has_more():
                console.print("[dim]  接口 hasMore=false，已到最后一页[/]")
                break

        captured = len(col.captured)
        console.print(f"[green]✓ 共捕获 {captured} 个搜索响应[/]")

        # 存完整捕获（带 URL），方便事后判断翻页有没有真的往前走
        dump_json("data/raw/boss_api_capture.json", col.captured)

        # ---- 解析 ----
        postings = []
        for payload in col.payloads():
            try:
                postings.extend(adapter.parse_api_joblist(payload))
            except RiskControlError as e:
                console.print(f"[red]{e}[/]")
                console.print("[red]已停止，不要马上重试。[/]")
                status = "risk_control"
                return {"new": 0, "updated": 0, "status": status}
            except ValueError as e:
                console.print(f"[yellow]跳过一条响应：{e}[/]")

        merged = {p.dedupe_key: p for p in postings}
        postings = list(merged.values())
        console.print(f"[green]✓ 解析到 {len(postings)} 条岗位（本批去重后）[/]")

        if store:
            for p in postings:
                if store.upsert(p, run_id):
                    new_count += 1
                else:
                    upd_count += 1
            console.print(
                f"[green]✓ 入库[/] 新增 [bold]{new_count}[/] 条，更新 {upd_count} 条，"
                f"库内共 {store.count()} 条"
            )
        return {"new": new_count, "updated": upd_count, "status": status}
    finally:
        if store:
            store.finish_run(
                run_id,
                pages=pages_done,
                captured=captured,
                new_count=new_count,
                updated_count=upd_count,
                status=status,
            )
            store.close()
        col.close()  # 只断开连接，不关你的浏览器


@app.command()
def watch(
    keyword: str = typer.Option("Agent开发", help="搜索关键词"),
    city: str = typer.Option("广州", help="城市"),
    port: int = typer.Option(9222, help="远程调试端口"),
    minutes: int = typer.Option(15, help="最长监听分钟数"),
    save: bool = typer.Option(True, help="结束时是否入库"),
) -> None:
    """实时监听：你在浏览器里手动滚动翻页，程序只负责记录。

    为什么不用程序滚动？
    BOSS 的搜索页在程序化滚动时会重置路由、把 scrollY 清零，
    翻页根本不触发（实测：滚 12 次，卡片数一直是 15）。
    人工滚动反而稳定，而且完全符合「人在环」的边界。
    """
    if not is_cdp_alive(port):
        console.print(f"[red]端口 {port} 上没有浏览器，先双击 start_browser.bat[/]")
        raise typer.Exit(code=1)

    adapter = BossAdapter()
    url = adapter.search_url(SearchQuery(keyword=keyword, city=city))

    try:
        col = CdpCollector(port=port, match="joblist.json")
    except Exception as e:
        console.print(f"[red]连不上浏览器：{e}[/]")
        raise typer.Exit(code=1) from None

    run_id = time.strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:6]
    store = Storage(settings.db_path) if save else None
    if store:
        store.start_run(run_id, keyword, city)

    new_count = 0
    upd_count = 0
    status = "ok"
    last = 0

    try:
        try:
            col.open(url)
        except Exception as e:
            console.print(f"[red]打不开页面：{e}[/]")
            raise typer.Exit(code=1) from None

        if not col.wait_for_data(timeout_s=40):
            console.print("[yellow]还没捕获到搜索接口。请确认已登录、页面在产品列表页。[/]")
            raise typer.Exit(code=1)

        console.print(f"[green]✓ 开始监听[/]  {keyword} @ {city}")
        console.print("[bold yellow]现在请在浏览器里往下滚动，越往下翻得越多。[/]")
        console.print(f"[dim]最多监听 {minutes} 分钟，随时 Ctrl+C 结束。[/]")

        deadline = time.time() + minutes * 60
        try:
            while time.time() < deadline:
                n = len(col.captured)
                if n != last:
                    total = col.total_count()
                    console.print(
                        f"[dim]  已捕获 {n} 个响应"
                        + (f"（接口总量 {total}）" if total else "")
                        + "[/]"
                    )
                    last = n
                if not col.has_more() and n > 1:
                    console.print("[dim]  接口 hasMore=false，到底了[/]")
                    break
                col.pump(2)
        except KeyboardInterrupt:
            console.print("\n[dim]收到中断，收尾中…[/]")

        postings = []
        for payload in col.payloads():
            try:
                postings.extend(adapter.parse_api_joblist(payload))
            except RiskControlError as e:
                console.print(f"[red]{e}[/]")
                status = "risk_control"
                break
            except ValueError:
                continue

        merged = {p.dedupe_key: p for p in postings}
        postings = list(merged.values())
        console.print(f"[green]✓ 共 {len(postings)} 条岗位（去重后）[/]")

        if store:
            for p in postings:
                if store.upsert(p, run_id):
                    new_count += 1
                else:
                    upd_count += 1
            console.print(
                f"[green]✓ 入库[/] 新增 [bold]{new_count}[/] 条，更新 {upd_count} 条，"
                f"库内共 {store.count()} 条"
            )
    finally:
        if store:
            store.finish_run(
                run_id,
                captured=len(col.captured),
                new_count=new_count,
                updated_count=upd_count,
                status=status,
            )
            store.close()
        col.close()


def _print_postings(postings, limit: int = 15) -> None:
    table = Table(show_lines=False)
    table.add_column("#", justify="right", style="dim")
    table.add_column("岗位", style="cyan", max_width=28)
    table.add_column("公司", max_width=18)
    table.add_column("薪资", justify="right")
    table.add_column("城市")
    table.add_column("技能", max_width=26)
    for i, p in enumerate(postings[:limit], 1):
        table.add_row(
            str(i),
            p.title,
            p.company,
            p.salary_raw or "-",
            f"{p.city or '-'}·{p.district or ''}".rstrip("·"),
            ",".join(p.skills[:4]),
        )
    console.print(table)
    if len(postings) > limit:
        console.print(f"[dim]…仅显示前 {limit} 条，共 {len(postings)} 条[/]")


if __name__ == "__main__":
    app()
