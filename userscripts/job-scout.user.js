// ==UserScript==
// @name         job-scout 采集器
// @version      0.10.5
// @namespace    job-scout.local
// @description  旁听 BOSS 直聘职位接口，自动滚动翻页，循环补全 JD 正文，推送到本地 job-scout
// @match        https://www.zhipin.com/*
// @run-at       document-start
// @grant        none
// ==/UserScript==

(function () {
  'use strict';

  // 采集服务端口：8765 常被本地其它工具占用（比如 adb 桥），
  // 所以启动时依次探测，认「/health 里有 total 字段」的那个。
  const API_PORTS = [8766, 8765, 8767, 8768];
  let API = 'http://127.0.0.1:8766';
  let ENDPOINT = API + '/ingest';
  let HEALTH = API + '/health';
  const AUTORUN_KEY = 'jobscout.autorun';

  /** 探测哪个端口是 job-scout 的接收服务。返回 true 表示找到了。 */
  async function probeApi() {
    for (const port of API_PORTS) {
      try {
        const r = await fetch(`http://127.0.0.1:${port}/health`, {
          cache: 'no-store',
          signal: AbortSignal.timeout(1500),
        });
        if (!r.ok) continue;
        const d = await r.json();
        // 我们的 /health 一定带 total；别的服务没有这个字段
        if (typeof d.total === 'number') {
          API = `http://127.0.0.1:${port}`;
          ENDPOINT = API + '/ingest';
          HEALTH = API + '/health';
          return true;
        }
      } catch (e) {}
    }
    return false;
  }

  const state = {
    jobs: new Map(),
    total: null,
    dirty: false,
    lastMsg: '',
    autoPush: true,
    timer: null,
    idle: 0,
    lastCount: 0,
    jdRunning: false,
    jdStop: false,
    blockedUntil: 0,
    lastJobUrl: '',
    jdFailWarned: false,
    autoStop: true,
    target: 0,
    debugDumped: false,
    autoRun: false,
    detailDumped: false,
    testing: false,
    onlyIntern: true,
    onlyRelevant: true,
    skippedNonIntern: 0,
    skippedIrrelevant: 0,
    navDumped: false,
  };

  // ---------- 设置持久化 ----------
  const LS_KEY = 'jobscout.cfg';

  function loadCfg() {
    try {
      const c = JSON.parse(localStorage.getItem(LS_KEY) || '{}');
      if (typeof c.target === 'number') state.target = c.target;
      if (typeof c.autoStop === 'boolean') state.autoStop = c.autoStop;
      if (typeof c.autoPush === 'boolean') state.autoPush = c.autoPush;
      if (typeof c.onlyIntern === 'boolean') state.onlyIntern = c.onlyIntern;
      if (typeof c.onlyRelevant === 'boolean') state.onlyRelevant = c.onlyRelevant;
      if (typeof c.blockedUntil === 'number') state.blockedUntil = c.blockedUntil;
      if (typeof c.lastJobUrl === 'string') state.lastJobUrl = c.lastJobUrl;
      if (state.blockedUntil && state.blockedUntil <= Date.now()) state.blockedUntil = 0;
    } catch (e) {}
  }

  function saveCfg() {
    try {
      localStorage.setItem(
        LS_KEY,
        JSON.stringify({
          target: state.target,
          autoStop: state.autoStop,
          autoPush: state.autoPush,
          onlyIntern: state.onlyIntern,
          onlyRelevant: state.onlyRelevant,
          blockedUntil: state.blockedUntil,
          lastJobUrl: state.lastJobUrl,
        })
      );
    } catch (e) {}
  }

  loadCfg();

  // ---------- 自动模式 ----------
  // 由 `job-scout auto` 生成的 URL 带 ?jobscout=auto 触发；
  // 标记存在 localStorage，登录跳转后也能恢复。
  function setAutoRun(on) {
    state.autoRun = on;
    try {
      if (on) localStorage.setItem(AUTORUN_KEY, '1');
      else localStorage.removeItem(AUTORUN_KEY);
    } catch (e) {}
  }

  function autoRunEnabled() {
    try {
      return localStorage.getItem(AUTORUN_KEY) === '1';
    } catch (e) {
      return false;
    }
  }

  function isJobListPage() {
    return /\/web\/geek\/job/.test(location.pathname);
  }

  function bootAutoRun() {
    // 导航模式进行中，别又触发自动滚动
    if (loadQueue()) return;

    const p = new URLSearchParams(location.search);
    if (p.get('jobscout') === 'auto') setAutoRun(true);
    if (!autoRunEnabled()) return;

    state.autoRun = true;

    if (!isJobListPage()) {
      // 可能在登录页，等跳转到列表页再说
      state.lastMsg = '自动模式：等待进入岗位列表页（请先完成登录）';
      render();
      return;
    }

    state.lastMsg = '自动模式：4 秒后开始滚动';
    render();
    setTimeout(() => {
      if (state.autoRun && !state.timer && !state.jdRunning) startAuto();
    }, 4000);
  }

  // ---------- 数据归一化 ----------
  // BOSS 列表接口的 jobType：4 = 实习，0 = 全职，5 = 其它
  const JOB_TYPE_INTERN = 4;

  // 相关性关键词：标题/技能里得沾上 AI 相关，否则是模糊搜索混进来的
  const RELEVANT_KEYWORDS = [
    'agent', 'ai', '大模型', 'llm', 'rag', '机器学习', '算法', '智能',
    'nlp', 'prompt', '多模态', 'aigc', '深度学习', '神经网络', '知识库',
  ];

  // 非技术岗黑名单：带 AI 也不要（销售 / 助教 / 运营 / 产品 / 设计…）
  const NON_TECH_KEYWORDS = [
    '销售', '助教', '客服', '运营', '产品经理', '产品实习', '设计师', '设计实习',
    '策划', '招聘', 'hr', '行政', '财务', '市场', '商务', 'bd', '讲师', '教务',
    '文案', '编辑', '新媒体', '直播',
  ];

  function isRelevant(j) {
    const text = ((j.jobName || '') + ' ' + (Array.isArray(j.skills) ? j.skills.join(' ') : '')).toLowerCase();
    if (NON_TECH_KEYWORDS.some((k) => text.includes(k))) return false;
    return RELEVANT_KEYWORDS.some((k) => text.includes(k));
  }

  function normalize(j) {
    const id = j.encryptJobId || j.jobId;
    if (!id || !j.jobName) return null;

    // 只收实习，省下 JD 抓取额度（可在面板关掉）
    if (state.onlyIntern) {
      const jt = j.jobType;
      const isIntern = Number(jt) === JOB_TYPE_INTERN || /实习/.test(j.jobName);
      if (!isIntern) {
        state.skippedNonIntern = (state.skippedNonIntern || 0) + 1;
        return null;
      }
    }

    // 只要 AI/Agent 相关的，挡掉产品/设计/运营这类模糊匹配
    if (state.onlyRelevant && !isRelevant(j)) {
      state.skippedIrrelevant = (state.skippedIrrelevant || 0) + 1;
      return null;
    }

    return {
      job_id: String(id),
      title: j.jobName,
      company: j.brandName || '',
      salary: j.salaryDesc || '',
      city: j.cityName || '',
      district: j.areaDistrict || '',
      experience: j.jobExperience || '',
      education: j.jobDegree || '',
      job_type: j.jobType,
      skills: Array.isArray(j.skills) ? j.skills : [],
      description: '',
      security_id: j.securityId || '',
      url:
        'https://www.zhipin.com/job_detail/' +
        id +
        '.html' +
        (j.securityId ? '?securityId=' + j.securityId : ''),
    };
  }

  function ingest(payload) {
    if (!payload || !payload.zpData) return;
    const list = payload.zpData.jobList || [];
    let added = 0;
    for (const raw of list) {
      const job = normalize(raw);
      if (!job) continue;
      if (state.jobs.has(job.job_id)) {
        const old = state.jobs.get(job.job_id);
        job.description = old.description || '';
      } else {
        added++;
      }
      state.jobs.set(job.job_id, job);
    }
    if (typeof payload.zpData.totalCount === 'number') {
      if (state.total !== payload.zpData.totalCount) {
        state.idle = 0;
        state.lastCount = state.jobs.size;
      }
      state.total = payload.zpData.totalCount;
    }
    if (added > 0) state.dirty = true;
    render();
  }

  // ---------- 钩子：fetch ----------
  const origFetch = window.fetch;
  window.fetch = function (...args) {
    const p = origFetch.apply(this, args);
    try {
      const url = typeof args[0] === 'string' ? args[0] : (args[0] && args[0].url) || '';
      if (url.includes('joblist.json')) {
        p.then((res) => res.clone().json().then(ingest).catch(() => {})).catch(() => {});
      }
    } catch (e) {}
    return p;
  };

  // ---------- 钩子：XMLHttpRequest ----------
  const XHR = window.XMLHttpRequest;
  const origOpen = XHR.prototype.open;
  const origSend = XHR.prototype.send;
  XHR.prototype.open = function (method, url) {
    this.__jsUrl = url;
    return origOpen.apply(this, arguments);
  };
  XHR.prototype.send = function () {
    this.addEventListener('load', () => {
      try {
        const url = String(this.__jsUrl || '') + ' ' + String(this.responseURL || '');
        if (url.includes('joblist.json')) {
          ingest(JSON.parse(this.responseText));
        }
      } catch (e) {}
    });
    return origSend.apply(this, arguments);
  };

  // ---------- 推送 ----------
  async function push() {
    const jobs = Array.from(state.jobs.values());
    if (!jobs.length) {
      state.lastMsg = '还没有数据';
      render();
      return;
    }
    try {
      const res = await fetch(ENDPOINT, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ jobs }),
      });
      const data = await res.json();
      state.dirty = false;
      state.lastMsg = `已推送：新增 ${data.new} 条，库内共 ${data.total} 条`;
    } catch (e) {
      state.lastMsg = '推送失败：本地服务没开？先运行 job-scout serve';
    }
    render();
  }

  function exportJson() {
    const blob = new Blob([JSON.stringify({ jobs: Array.from(state.jobs.values()) }, null, 2)], {
      type: 'application/json',
    });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `job-scout-${Date.now()}.json`;
    a.click();
    setTimeout(() => URL.revokeObjectURL(a.href), 5000);
  }

  // ---------- 自动滚动 ----------
  const SCROLL_STEP = 900;
  const SCROLL_INTERVAL = 1800;
  const IDLE_LIMIT = 20;

  function scrollStep() {
    try {
      if (state.idle >= 3) window.scrollBy(0, -600);
    } catch (e) {}
    try {
      window.scrollBy(0, SCROLL_STEP);
    } catch (e) {}
    try {
      document.querySelectorAll('div, ul').forEach((el) => {
        if (el.scrollHeight > el.clientHeight + 200 && el.clientHeight > 200) {
          el.scrollTop = el.scrollTop + SCROLL_STEP;
        }
      });
    } catch (e) {}
  }

  function tick() {
    const n = state.jobs.size;
    if (n === state.lastCount) state.idle++;
    else {
      state.idle = 0;
      state.lastCount = n;
    }

    if (state.target > 0 && n >= state.target) {
      stopAuto('已达到目标 ' + state.target + ' 条');
      return;
    }
    if (state.autoStop && state.idle >= IDLE_LIMIT) {
      stopAuto('连续 ' + IDLE_LIMIT + ' 轮没有新岗位，停止（当前累计 ' + n + ' 条）');
      return;
    }

    scrollStep();
    render();
  }

  function startAuto() {
    if (state.timer) return;
    state.idle = 0;
    state.lastCount = state.jobs.size;
    state.lastMsg = '自动滚动中…';
    state.timer = setInterval(tick, SCROLL_INTERVAL);
    render();
  }

  function stopAuto(reason, manual) {
    if (state.timer) {
      clearInterval(state.timer);
      state.timer = null;
    }
    state.lastMsg = reason || '已停止自动滚动';
    if (state.dirty) push();
    render();

    // 自动模式：滚动结束 → 接着用「导航模式」抓 JD（最稳，慢但不容易被拦）
    if (state.autoRun && !manual && !state.jdRunning && !loadQueue()) {
      state.lastMsg += ' → 2 秒后自动抓 JD（导航模式）';
      render();
      setTimeout(() => {
        if (state.autoRun && !state.jdRunning && !loadQueue()) {
          startNavMode(300).catch(() => {});
        }
      }, 2000);
    }
  }

  // ================= JD 正文 =================
  // 接口虽轻，但账号/IP 的累计风险分是共享的，频率必须压下来
  const JD_DELAY_MIN = 12000;
  const JD_DELAY_MAX = 20000;
  const JD_MAX_ROUNDS = 100;

  function sleep(ms) {
    return new Promise((r) => setTimeout(r, ms));
  }

  async function fetchPending(limit) {
    try {
      const res = await fetch(API + '/pending?limit=' + limit);
      if (!res.ok) return { ok: false, jobs: [] };
      const data = await res.json();
      if (!Array.isArray(data.jobs)) return { ok: false, jobs: [] };
      return { ok: true, jobs: data.jobs };
    } catch (e) {
      return { ok: false, jobs: [] };
    }
  }

  async function pushJD(items) {
    if (!items.length) return;
    try {
      await fetch(API + '/jd', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ items }),
      });
    } catch (e) {}
  }

  async function pushJDFail(jobIds) {
    if (!jobIds.length) return;
    try {
      const res = await fetch(API + '/jd-fail', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ job_ids: jobIds }),
      });
      if (!res.ok && !state.jdFailWarned) {
        state.jdFailWarned = true;
        state.lastMsg = '服务端没有 /jd-fail 接口，失败记录不生效 —— 建议重启 serve';
        render();
      }
    } catch (e) {}
  }

  async function dumpFailSample(job, html) {
    if (state.debugDumped || !html) return;
    state.debugDumped = true;
    try {
      await fetch(API + '/debug', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: job.url, html: html.slice(0, 300000) }),
      });
    } catch (e) {}
  }

  // BOSS 风控返回码（参考社区接口文档）
  const RISK_CODES = {
    9: '频率限制',
    31: 'IP 限制',
    32: '账号限制',
    36: '账号风险',
    37: '登录过期',
  };

  function htmlToText(s) {
    const d = document.createElement('div');
    d.innerHTML = s;
    return (d.textContent || '').replace(/\s+/g, ' ').trim();
  }

  /** 从 detail.json 找 JD 正文。字段名不确定时深度搜索最长的候选。 */
  function pickDescription(data) {
    const z = (data && data.zpData) || {};
    const direct = [
      z.jobDetail && z.jobDetail.description,
      z.jobInfo && z.jobInfo.description,
      z.description,
      z.postDescription,
    ];
    for (const c of direct) {
      if (typeof c === 'string' && htmlToText(c).length > 40) return c;
    }
    let best = '';
    const stack = [z];
    let guard = 0;
    while (stack.length && guard++ < 200) {
      const cur = stack.pop();
      if (!cur || typeof cur !== 'object') continue;
      for (const k in cur) {
        const v = cur[k];
        if (typeof v === 'string' && v.length > best.length) best = v;
        else if (v && typeof v === 'object') stack.push(v);
      }
    }
    return htmlToText(best).length > 40 ? best : '';
  }

  async function dumpDetailSample(job, raw) {
    try {
      await fetch(API + '/debug', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          url: 'detail.json ' + job.job_id,
          html: (typeof raw === 'string' ? raw : JSON.stringify(raw)).slice(0, 20000),
        }),
      });
    } catch (e) {}
  }

  /** 走 JSON 接口抓 JD：比整页 HTML 轻得多，请求特征也和正常前端一致。 */
  async function fetchOneJDApi(job) {
    const sid = job.security_id || '';
    const url =
      '/wapi/zpgeek/job/detail.json?encryptJobId=' +
      encodeURIComponent(job.job_id) +
      (sid ? '&securityId=' + encodeURIComponent(sid) : '');

    let res;
    try {
      res = await fetch(url, {
        credentials: 'include',
        headers: { Accept: 'application/json, text/plain, */*' },
      });
    } catch (e) {
      return { text: '', reason: '网络错误', fallback: true };
    }

    if (!res.ok) return { text: '', reason: 'HTTP ' + res.status, fallback: true };

    let data;
    try {
      data = await res.json();
    } catch (e) {
      return { text: '', reason: '接口非 JSON', fallback: true };
    }

    const code = data && data.code;
    // 频率限制是暂时的，歇一会儿能继续；其它风控码说明账号/IP 被盯上了
    if (code === 9) {
      return { text: '', reason: '风控·频率限制(9)', blocked: true, rateLimited: true };
    }
    if (RISK_CODES[code]) {
      return { text: '', reason: '风控·' + RISK_CODES[code] + '(' + code + ')', blocked: true };
    }
    if (code !== 0 && code != null) {
      return {
        text: '',
        reason: '接口 code=' + code + (data.message ? ' ' + data.message : ''),
        fallback: true,
      };
    }

    const desc = pickDescription(data);
    if (!desc) {
      // 第一次解析失败时把真实结构上报，方便对症下药
      if (!state.detailDumped) {
        state.detailDumped = true;
        dumpDetailSample(job, data);
      }
      return { text: '', reason: '接口字段未识别', fallback: true };
    }

    const text = htmlToText(desc);
    if (text.length <= 40) return { text: '', reason: '内容过短', fallback: true };
    return { text, reason: '' };
  }

  /** 兜底：抓整页 HTML 解析 DOM（旧的笨办法）。 */
  async function fetchOneJDHtml(job) {
    let res;
    try {
      res = await fetch(job.url, { credentials: 'include' });
    } catch (e) {
      return { text: '', reason: '网络错误' };
    }

    const html = await res.text();
    if (!res.ok) return { text: '', reason: 'HTTP ' + res.status };
    if (/登录查看完整内容|安全验证|环境存在异常|访问频繁/.test(html)) {
      return { text: '', reason: '被拦截', blocked: true };
    }
    // BOSS 的人机校验挑战页：标题「请稍候」，正文只有「正在加载中」
    if (!/job-sec-text/.test(html) && /请稍候|正在加载中|passport_page_error/.test(html)) {
      return { text: '', reason: '人机校验', blocked: true };
    }

    const doc = new DOMParser().parseFromString(html, 'text/html');
    const el = doc.querySelector('.job-sec-text, .job-detail-section .text, .job-detail-section');
    if (!el) return { text: '', reason: '选择器未命中', html };

    const text = (el.textContent || '').replace(/\s+/g, ' ').trim();
    if (text.length <= 40) return { text: '', reason: '内容过短', html };
    return { text, reason: '', html: '' };
  }

  async function fetchOneJD(job) {
    // 优先 JSON 接口；接口这条路走不通才回退整页 HTML
    const r = await fetchOneJDApi(job);
    if (r.text || r.blocked) return r;
    const h = await fetchOneJDHtml(job);
    return { ...h, usedHtml: true };
  }

  async function processJDList(jobs, roundNo) {
    let ok = 0;
    let fail = 0;
    let blockStreak = 0;
    let batch = [];
    let failIds = [];
    const reasons = {};

    for (let i = 0; i < jobs.length; i++) {
      if (state.jdStop) {
        if (batch.length) await pushJD(batch);
        if (failIds.length) await pushJDFail(failIds);
        return { ok, fail, reasons, stopped: true, blocked: false };
      }

      const job = jobs[i];
      state.lastJobUrl = job.url || '';
      const r = await fetchOneJD(job);

      if (r.text) {
        batch.push({
          job_id: job.job_id,
          description: r.text,
          title: job.title,
          company: job.company,
          url: job.url,
        });
        ok++;
      } else {
        fail++;
        failIds.push(job.job_id);
        reasons[r.reason] = (reasons[r.reason] || 0) + 1;
        await dumpFailSample(job, r.html);

        if (r.blocked) {
          // 频率限制：歇 5 分钟后接着抓，不算账号被封
          if (r.rateLimited) {
            state.lastMsg = '触发频率限制，暂停 5 分钟后继续…（可随时点停止）';
            render();
            await sleep(300000);
            blockStreak = 0;
            continue;
          }
          blockStreak++;
          // 接口明确返回风控码时，连续 2 次就停，别把账号搞进小黑屋
          if (blockStreak >= 2) {
            if (batch.length) await pushJD(batch);
            if (failIds.length) await pushJDFail(failIds);
            return { ok, fail, reasons, stopped: false, blocked: true };
          }
          state.lastMsg = '遇到风控（' + (r.reason || '') + '），暂停 120 秒后重试一次…';
          render();
          await sleep(120000);
        } else if (r.reason === '被拦截' || r.reason === '人机校验') {
          blockStreak++;
          if (blockStreak >= 6) {
            if (batch.length) await pushJD(batch);
            if (failIds.length) await pushJDFail(failIds);
            return { ok, fail, reasons, stopped: false, blocked: true };
          }
          if (blockStreak === 3) {
            state.lastMsg = '连续被拦截/人机校验，暂停 120 秒…';
            render();
            await sleep(120000);
          }
        } else {
          blockStreak = 0;
        }
      }

      const tail = Object.entries(reasons)
        .map(([k, v]) => `${k} ${v}`)
        .join('，');
      state.lastMsg = `第 ${roundNo} 轮 ${i + 1}/${jobs.length}｜成功 ${ok}｜失败 ${fail}${
        tail ? '（' + tail + '）' : ''
      }`;
      render();

      if (batch.length >= 5) {
        await pushJD(batch);
        batch = [];
      }
      if (failIds.length >= 10) {
        await pushJDFail(failIds);
        failIds = [];
      }
      await sleep(JD_DELAY_MIN + Math.random() * (JD_DELAY_MAX - JD_DELAY_MIN));

      // 每 8 条歇一会儿，避免密集请求触发人机校验
      if ((i + 1) % 8 === 0 && i + 1 < jobs.length) {
        state.lastMsg = `已抓 ${i + 1} 条，休息 90 秒降低风控…`;
        render();
        await sleep(90000);
      }
    }

    if (batch.length) await pushJD(batch);
    if (failIds.length) await pushJDFail(failIds);
    return { ok, fail, reasons, stopped: false, blocked: false };
  }

  // ================= 导航模式 =================
  // 真实导航到详情页再抓 DOM，和最手动点击的行为一致。
  // 接口 fetch 会被风控，但真导航不会——因为页面自己会发那个请求。
  const QKEY = 'jobscout.jdqueue';

  function loadQueue() {
    try {
      return JSON.parse(localStorage.getItem(QKEY) || 'null');
    } catch (e) {
      return null;
    }
  }

  function saveQueue(q) {
    try {
      localStorage.setItem(QKEY, JSON.stringify(q));
    } catch (e) {}
  }

  function clearQueue() {
    try {
      localStorage.removeItem(QKEY);
    } catch (e) {}
  }

  function isDetailPage() {
    return /\/job_detail\//.test(location.pathname);
  }

  function readDetailDom() {
    const el = document.querySelector(
      '.job-sec-text, .job-detail-section .text, .job-detail-section',
    );
    if (!el) return '';
    // 用 innerText：只读可见文本，自动跳过 display:none 的 CSS 和水印 span。
    // textContent 会把隐藏的 <style> 和 kanzhun/boss 水印一起读出来。
    const raw = el.innerText || el.textContent || '';
    return raw.replace(/\s+/g, ' ').trim();
  }

  /** 从详情页 URL 里取 job_id：/job_detail/<id>.html */
  function jobIdFromUrl() {
    const m = location.pathname.match(/\/job_detail\/([^/.]+)\.html/);
    return m ? m[1] : '';
  }

  // ================= 自动选中「实习」筛选 =================
  // BOSS 搜索页的 URL 没有可靠的 jobType 参数，只能点页面上的筛选控件。
  // 做法：找到「求职类型」这一组的标签，在同组里点「实习」。
  async function ensureInternFilter() {
    const params = new URLSearchParams(location.search);
    if (params.get('jobscout') !== 'auto' || params.get('intern') !== '1') {
      return false;
    }

    for (let round = 0; round < 16; round++) {
      // 找写着「求职类型」的元素
      const label = Array.from(
        document.querySelectorAll('span, div, dt, label'),
      ).find((el) => el.children.length === 0 && el.textContent.trim() === '求职类型');

      if (label) {
        // 往上找两三层，拿到整组筛选项
        let box = label.parentElement;
        for (let i = 0; i < 3 && box && !box.querySelector('a, li'); i++) {
          box = box.parentElement;
        }
        if (box) {
          const opts = Array.from(box.querySelectorAll('a, li, span')).filter(
            (el) => el.textContent.trim() === '实习',
          );
          for (const opt of opts) {
            const cls = String(opt.className || '');
            if (cls.includes('active') || cls.includes('checked') || cls.includes('selected')) {
              state.lastMsg = '「实习」筛选已选中';
              render();
              return true;
            }
          }
          if (opts.length) {
            opts[0].click();
            state.lastMsg = '已自动选中「实习」筛选，等列表刷新…';
            render();
            await sleep(2500);
            return true;
          }
        }
      }
      await sleep(500);
    }

    state.lastMsg = '没找到「求职类型 → 实习」筛选，请手动点一下（脚本会继续按接口过滤）';
    render();
    return false;
  }

  // ================= 单条定点抓取 =================
  // 由网页端「抓取这条 JD」按钮打开：?jobscout=one
  // 只抓当前这一页，抓完显示结果，不影响队列和自动模式
  async function oneShotGrab() {
    const jobId = jobIdFromUrl();
    if (!jobId) {
      state.lastMsg = '这不是岗位详情页，没法定点抓取';
      render();
      return;
    }

    state.lastMsg = '定点抓取：等待正文渲染…';
    render();

    let text = '';
    for (let i = 0; i < 24; i++) {
      text = readDetailDom();
      if (text.length > 40) break;
      await sleep(500);
    }

    if (text.length <= 40) {
      state.lastMsg = '✗ 没找到 JD 正文（可能是人机校验页，刷新重试一次）';
      render();
      return;
    }

    const title = (document.querySelector('.job-banner .name, h1')?.textContent || '').trim();
    const company = (document.querySelector('.company-info .name, .job-boss-info .name')?.textContent || '').trim();

    await pushJD([
      { job_id: jobId, description: text, title, company, url: location.href.split('?')[0] },
    ]);

    state.lastMsg = `✓ 已抓取 ${text.length} 字，已同步到本地，可以关掉这个页面`;
    render();
    // 标签页标题给个提示
    document.title = `[已抓取] ${document.title}`;
  }

  async function startNavMode(limit) {
    if (state.jdRunning) return;
    const pending = await fetchPending(limit);
    if (!pending.ok) {
      state.lastMsg = '✗ 本地服务没有 /pending，先重启采集服务';
      render();
      return;
    }
    if (!pending.jobs.length) {
      state.lastMsg = '✓ 没有待补岗位了';
      render();
      return;
    }

    const q = {
      jobs: pending.jobs,
      idx: 0,
      returnUrl: location.href.split('#')[0],
      startedAt: Date.now(),
      ok: 0,
      fail: 0,
    };
    saveQueue(q);
    state.lastMsg = `导航模式：共 ${q.jobs.length} 条，2 秒后跳转第 1 条…`;
    render();
    await sleep(2000);
    location.href = q.jobs[0].url;
  }

  async function grabOnDetailPage() {
    const q = loadQueue();
    if (!q || q.idx >= q.jobs.length) return;

    // SPA 渲染，等正文出现（最多 10 秒）
    let text = '';
    for (let i = 0; i < 20; i++) {
      text = readDetailDom();
      if (text.length > 40) break;
      await sleep(500);
    }

    const job = q.jobs[q.idx];
    if (text.length > 40) {
      await pushJD([
        {
          job_id: job.job_id,
          description: text,
          title: job.title,
          company: job.company,
          url: job.url,
        },
      ]);
      q.ok++;
      state.lastMsg = `✓ ${q.idx + 1}/${q.jobs.length} 抓到 ${text.length} 字`;
    } else {
      await pushJDFail([job.job_id]);
      q.fail++;
      state.lastMsg = `✗ ${q.idx + 1}/${q.jobs.length} 没抓到正文`;
      // 第一次失败把页面结构报上去，方便确认选择器有没有变
      if (!state.navDumped) {
        state.navDumped = true;
        try {
          await fetch(API + '/debug', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              url: 'navmode ' + location.href,
              html: document.documentElement.outerHTML.slice(0, 60000),
            }),
          });
        } catch (e) {}
      }
    }
    render();

    q.idx++;
    saveQueue(q);

    // 每 6 条多歇一会儿
    const pause = q.idx % 6 === 0 ? 8000 : 2500;
    await sleep(pause + Math.random() * 2000);
    location.href = q.returnUrl;
  }

  async function navModeStep() {
    const q = loadQueue();
    if (!q) return;

    if (isDetailPage()) {
      await grabOnDetailPage();
      return;
    }

    // 列表页：队列未空就继续下一条
    if (q.idx >= q.jobs.length) {
      clearQueue();
      state.lastMsg = `导航模式完成：成功 ${q.ok} 条，失败 ${q.fail} 条`;
      render();
      // 自动模式下抓完要回报，终端才知道可以生成日报了
      if (state.autoRun) {
        setAutoRun(false);
        fetch(API + '/auto-done', { method: 'POST' }).catch(() => {});
      }
      return;
    }
    state.lastMsg = `导航模式：${q.idx}/${q.jobs.length}，准备跳下一条…`;
    render();
    await sleep(1500 + Math.random() * 1500);
    location.href = q.jobs[q.idx].url;
  }

  /** 一轮抓完自动问下一批，直到库里没有缺 JD 的岗位。*/
  async function runJD() {
    if (state.jdRunning) return;

    state.jdRunning = true;
    state.jdStop = false;
    let totalOk = 0;
    let totalFail = 0;

    try {
      for (let round = 1; round <= JD_MAX_ROUNDS; round++) {
        state.lastMsg = `第 ${round} 轮：向服务端查询待补岗位…`;
        render();

        const pending = await fetchPending(300);

        if (!pending.ok) {
          state.lastMsg =
            '服务端没有 /pending 接口 —— 跑的还是旧代码。请在终端 Ctrl+C 后重新运行 job-scout serve。';
          render();
          return;
        }

        if (pending.jobs.length === 0) {
          state.lastMsg = `✓ 全部补全完成：本次成功 ${totalOk} 条，失败 ${totalFail} 条`;
          if (state.autoRun) {
            setAutoRun(false);
            state.lastMsg += '｜自动模式结束，可以关掉浏览器了';
            fetch(API + '/auto-done', { method: 'POST' }).catch(() => {});
          }
          render();
          return;
        }

        state.lastMsg = `第 ${round} 轮：本批 ${pending.jobs.length} 条待补`;
        render();

        const r = await processJDList(pending.jobs, round);
        totalOk += r.ok;
        totalFail += r.fail;

        if (r.stopped) {
          state.lastMsg = `已手动停止：本次成功 ${totalOk} 条，失败 ${totalFail} 条`;
          render();
          return;
        }
        if (r.blocked) {
          state.blockedUntil = Date.now() + 30 * 60 * 1000;
          saveCfg();
          state.lastMsg = `被风控拦住（本次成功 ${totalOk}）。30 分钟后自动重试；也可以点「打开验证页」手动过验证，然后直接再点抓取。`;
          render();
          return;
        }
        if (r.ok === 0) {
          const tail = Object.entries(r.reasons)
            .map(([k, v]) => `${k} ${v}`)
            .join('，');
          state.lastMsg = `本轮全部失败（${tail}），已停止。已抓到的不会丢。`;
          render();
          return;
        }

        state.lastMsg = `第 ${round} 轮完成：+${r.ok} 条，继续下一轮…`;
        render();
        await sleep(3000);
      }

      state.lastMsg = `达到最大轮数，已停止（成功 ${totalOk}）`;
      render();
    } finally {
      state.jdRunning = false;
      state.jdStop = false;
      render();
    }
  }

  // ---------- 面板 ----------
  let panel = null;
  let countEl = null;
  let msgEl = null;
  let btnEl = null;
  let jdBtn = null;

  function buildPanel() {
    if (panel || !document.body) return;
    panel = document.createElement('div');
    panel.id = 'js-panel';
    panel.style.cssText = [
      'position:fixed', 'right:18px', 'bottom:18px', 'z-index:2147483647',
      'background:#111827', 'color:#e5e7eb', 'border:1px solid #374151',
      'border-radius:10px', 'padding:12px 14px', 'font:13px/1.5 system-ui,sans-serif',
      'box-shadow:0 8px 24px rgba(0,0,0,.35)', 'min-width:250px',
    ].join(';');

    panel.innerHTML = `
      <div style="font-weight:600;margin-bottom:6px">job-scout 采集器</div>
      <div id="js-count" style="color:#9ca3af;margin-bottom:8px">已收集 0 条</div>
      <button id="js-auto" style="width:100%;padding:8px;border:0;border-radius:6px;background:#16a34a;color:#fff;cursor:pointer;margin-bottom:6px">开始自动滚动</button>
      <button id="js-jd" style="width:100%;padding:7px;border:0;border-radius:6px;background:#7c3aed;color:#fff;cursor:pointer;margin-bottom:6px">抓 JD 正文（循环补全）</button>
      <button id="js-nav" style="width:100%;padding:7px;border:0;border-radius:6px;background:#db2777;color:#fff;cursor:pointer;margin-bottom:6px">导航模式抓 JD（最稳，慢）</button>
      <button id="js-test" style="width:100%;padding:6px;border:0;border-radius:6px;background:#0ea5e9;color:#fff;cursor:pointer;margin-bottom:6px">测试详情接口（不占额度）</button>
      <button id="js-verify" style="width:100%;padding:6px;border:0;border-radius:6px;background:#4b5563;color:#fff;cursor:pointer;margin-bottom:6px">打开验证页（手动过验证）</button>
      <div style="display:flex;gap:6px;margin-bottom:6px">
        <button id="js-push" style="flex:1;padding:6px 8px;border:0;border-radius:6px;background:#2563eb;color:#fff;cursor:pointer">推送</button>
        <button id="js-export" style="flex:1;padding:6px 8px;border:0;border-radius:6px;background:#374151;color:#fff;cursor:pointer">导出</button>
      </div>
      <div style="display:flex;gap:6px;align-items:center;margin-bottom:6px;color:#9ca3af;font-size:12px">
        <span>目标</span>
        <input id="js-target" type="number" min="0" value="0"
               style="width:64px;background:#1f2937;border:1px solid #374151;color:#e5e7eb;border-radius:5px;padding:3px 6px;font-size:12px">
        <span>条（0=不限）</span>
      </div>
      <label style="display:flex;align-items:center;gap:6px;color:#9ca3af;font-size:12px;margin-bottom:4px">
        <input id="js-autostop" type="checkbox" checked> 无新增自动停
      </label>
      <label style="display:flex;align-items:center;gap:6px;color:#9ca3af;font-size:12px;margin-bottom:4px">
        <input id="js-onlyintern" type="checkbox" checked> 只收实习（jobType=4）
      </label>
      <label style="display:flex;align-items:center;gap:6px;color:#9ca3af;font-size:12px;margin-bottom:4px">
        <input id="js-onlyrelevant" type="checkbox" checked> 只要 AI/Agent 相关
      </label>
      <label style="display:flex;align-items:center;gap:6px;color:#9ca3af;font-size:12px">
        <input id="js-autopush" type="checkbox" checked> 自动推送
      </label>
      <div id="js-msg" style="color:#6b7280;font-size:11px;margin-top:6px"></div>
    `;
    document.body.appendChild(panel);

    countEl = panel.querySelector('#js-count');
    msgEl = panel.querySelector('#js-msg');
    btnEl = panel.querySelector('#js-auto');
    jdBtn = panel.querySelector('#js-jd');

    btnEl.addEventListener('click', () => {
      if (state.timer) {
        // 手动停止 = 退出自动模式，避免它自己又跑起来
        setAutoRun(false);
        stopAuto('手动停止', true);
      } else {
        startAuto();
      }
    });

    jdBtn.addEventListener('click', () => {
      if (state.jdRunning) {
        state.jdStop = true;
        setAutoRun(false);
        state.lastMsg = '正在停止…（当前这条抓完就停）';
        render();
      } else {
        state.blockedUntil = 0;
        runJD();
      }
    });

    panel.querySelector('#js-nav').addEventListener('click', () => {
      if (loadQueue()) {
        clearQueue();
        state.lastMsg = '已取消导航模式队列';
        render();
        return;
      }
      startNavMode(300);
    });

    panel.querySelector('#js-test').addEventListener('click', async () => {
      if (state.testing) return;
      state.testing = true;
      state.lastMsg = '测试详情接口中…';
      render();
      try {
        const pending = await fetchPending(1);
        if (!pending.ok) {
          state.lastMsg = '✗ 本地服务没有 /pending，先重启 job-scout serve';
          return;
        }
        if (!pending.jobs.length) {
          state.lastMsg = '✓ 没有待补岗位，说明都抓完了';
          return;
        }
        const job = pending.jobs[0];
        const r = await fetchOneJDApi(job);
        if (r.text) {
          state.lastMsg =
            '✓ 接口可用！抓到 ' + r.text.length + ' 字：' + r.text.slice(0, 50) + '…';
        } else {
          state.lastMsg = '✗ 接口失败：' + r.reason + '（会自动回退整页 HTML）';
        }
      } catch (e) {
        state.lastMsg = '✗ 测试异常：' + e;
      } finally {
        state.testing = false;
        render();
      }
    });

    panel.querySelector('#js-verify').addEventListener('click', () => {
      const url = state.lastJobUrl || 'https://www.zhipin.com/web/geek/jobs';
      window.open(url, '_blank');
    });

    const autopushEl = panel.querySelector('#js-autopush');
    const autostopEl = panel.querySelector('#js-autostop');
    const onlyInternEl = panel.querySelector('#js-onlyintern');
    const onlyRelevantEl = panel.querySelector('#js-onlyrelevant');
    const targetEl = panel.querySelector('#js-target');

    autopushEl.checked = state.autoPush;
    autostopEl.checked = state.autoStop;
    onlyInternEl.checked = state.onlyIntern;
    onlyRelevantEl.checked = state.onlyRelevant;
    targetEl.value = String(state.target);

    autopushEl.addEventListener('change', (e) => {
      state.autoPush = e.target.checked;
      saveCfg();
    });
    autostopEl.addEventListener('change', (e) => {
      state.autoStop = e.target.checked;
      saveCfg();
    });
    onlyInternEl.addEventListener('change', (e) => {
      state.onlyIntern = e.target.checked;
      saveCfg();
      state.lastMsg = state.onlyIntern
        ? '只收实习：非实习岗位会被跳过'
        : '注意：现在会收全职岗位';
      render();
    });
    onlyRelevantEl.addEventListener('change', (e) => {
      state.onlyRelevant = e.target.checked;
      saveCfg();
      state.lastMsg = state.onlyRelevant
        ? '只要 AI/Agent 相关：产品/设计等模糊结果会跳过'
        : '注意：现在会收所有实习岗（含产品/设计）';
      render();
    });
    targetEl.addEventListener('input', (e) => {
      state.target = parseInt(e.target.value, 10) || 0;
      saveCfg();
    });

    panel.querySelector('#js-push').addEventListener('click', push);
    panel.querySelector('#js-export').addEventListener('click', exportJson);

    render();
  }

  function render() {
    if (!countEl) return;
    const n = state.jobs.size;
    const withJd = Array.from(state.jobs.values()).filter((j) => j.description).length;
    countEl.textContent = `累计 ${n} 条｜本查询 ${state.total ?? '-'}｜有 JD ${withJd}`;
    msgEl.textContent = state.lastMsg;

    if (btnEl) {
      btnEl.textContent = state.timer ? '停止自动滚动' : '开始自动滚动';
      btnEl.style.background = state.timer ? '#dc2626' : '#16a34a';
    }
    if (jdBtn) {
      jdBtn.textContent = state.jdRunning ? '停止抓取' : '抓 JD 正文（循环补全）';
      jdBtn.style.background = state.jdRunning ? '#dc2626' : '#7c3aed';
    }
  }

  setInterval(() => {
    if (state.autoPush && state.dirty && state.jobs.size > 0 && !state.jdRunning) push();
  }, 8000);

  // 风控后 30 分钟自动重试；期间显示倒计时
  setInterval(() => {
    if (!state.blockedUntil) return;
    const left = state.blockedUntil - Date.now();
    if (left <= 0) {
      state.blockedUntil = 0;
      state.lastMsg = '自动重试开始…';
      render();
      runJD();
    } else {
      const m = Math.ceil(left / 60000);
      state.lastMsg = `被风控，${m} 分钟后自动重试；也可点「打开验证页」手动过验证后再点抓取`;
      render();
    }
  }, 10000);

  window.addEventListener('load', async () => {
    buildPanel();

    // 先找到真正的采集服务（8765 可能被别的工具占着）
    const found = await probeApi();
    if (!found) {
      state.lastMsg =
        '没找到 job-scout 采集服务（8766 / 8765 都不通）。先双击 start.bat，或看面板下方排查说明。';
      render();
      return;
    }

    fetch(HEALTH)
      .then((r) => r.json())
      .then((d) => {
        // 自动模式下保留状态提示，别被覆盖
        if (!state.autoRun) state.lastMsg = `本地服务已连接（库内 ${d.total} 条）`;
        render();
      })
      .catch(() => {
        state.lastMsg = '本地服务未启动：先运行 job-scout serve';
        render();
      });

    // 单条定点抓取优先：由网页端「抓取这条 JD」按钮打开
    const params = new URLSearchParams(location.search);
    if (params.get('jobscout') === 'one') {
      oneShotGrab();
      return;
    }

    // 自动模式：先把「求职类型」切成实习，再开始滚动
    if (params.get('jobscout') === 'auto') {
      await ensureInternFilter();
    }

    // 导航模式的队列优先：详情页抓完就走，列表页则继续下一条
    navModeStep();
    bootAutoRun();
  });

  const observer = new MutationObserver(() => buildPanel());
  observer.observe(document.documentElement, { childList: true, subtree: true });

  console.log('[job-scout] 采集器 v0.10.5 已注入（端口探测 + 定点抓取 + innerText）');
})();
