"use client";

import { Loader2, Settings2 } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { api, type CollectConfig } from "@/lib/api";

const ITEMS: { key: keyof CollectConfig; label: string; hint: string }[] = [
  {
    key: "only_intern",
    label: "只收实习岗",
    hint: "接口层只留 jobType=4，非实习直接跳过",
  },
  {
    key: "only_relevant",
    label: "只要 AI / Agent 相关",
    hint: "标题命中关键词才入库，挡掉产品/设计/运营",
  },
  {
    key: "auto_push",
    label: "抓到就推送",
    hint: "每 8 秒自动同步到本地库，不用手动点",
  },
  {
    key: "auto_stop",
    label: "无新增自动停",
    hint: "翻页没有新岗位时自动结束，省得一直挂着",
  },
];

/** 采集开关：油猴脚本打开时读这份配置。 */
export default function CollectSettings() {
  const [cfg, setCfg] = useState<CollectConfig | null>(null);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");

  const load = useCallback(async () => {
    try {
      setCfg((await api.collectConfig()).config);
    } catch {
      setCfg(null);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function toggle(key: keyof CollectConfig, value: boolean) {
    if (!cfg) return;
    const next = { ...cfg, [key]: value };
    setCfg(next);
    setBusy(true);
    try {
      await api.setCollectConfig({ [key]: value });
      setMsg("已保存，脚本下次打开页面时生效");
    } catch (e) {
      setMsg(`保存失败：${String(e)}`);
      await load();
    } finally {
      setBusy(false);
    }
  }

  async function changeTarget(v: number) {
    if (!cfg) return;
    setCfg({ ...cfg, target: v });
    await api.setCollectConfig({ target: v }).catch(() => undefined);
  }

  return (
    <section className="card p-5">
      <div className="flex items-center gap-2">
        <Settings2 size={15} className="text-fg3" />
        <h2 className="section-title">采集设置</h2>
        {busy && <Loader2 size={12} className="animate-spin text-fg3" />}
      </div>
      <p className="mt-1.5 text-xs leading-[1.7] text-fg3">
        这些开关存在本地，油猴脚本启动时会读。改完不用动脚本，刷新 BOSS 页面即可。
      </p>

      {!cfg ? (
        <p className="mt-4 text-2xs text-fg3">{msg || "读不到配置，后端服务起了吗？"}</p>
      ) : (
        <div className="mt-4 space-y-3">
          {ITEMS.map((it) => (
            <label
              key={it.key}
              className="flex cursor-pointer items-start gap-2.5 text-xs leading-[1.7]"
            >
              <input
                type="checkbox"
                checked={Boolean(cfg[it.key])}
                onChange={(e) => toggle(it.key, e.target.checked)}
                className="mt-0.5 h-3.5 w-3.5 shrink-0 cursor-pointer accent-[#4f8cff]"
              />
              <span>
                <span className="text-fg2">{it.label}</span>
                <span className="ml-1.5 text-2xs text-fg3">{it.hint}</span>
              </span>
            </label>
          ))}

          <div className="flex items-center gap-2 border-t border-line/60 pt-3 text-xs text-fg2">
            <span>目标条数</span>
            <input
              type="number"
              min={0}
              max={10000}
              value={cfg.target}
              onChange={(e) => changeTarget(Number(e.target.value) || 0)}
              className="input h-7 w-20 py-0 text-2xs"
            />
            <span className="text-2xs text-fg3">条（0 = 不限）</span>
          </div>

          {msg && <p className="text-2xs text-accent">{msg}</p>}
        </div>
      )}
    </section>
  );
}
