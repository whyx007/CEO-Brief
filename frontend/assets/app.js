const state = {
  today: null,

  marketSnapshot: null,
  fxSnapshot: null,
  targets: null,
  prompts: null,
  companyQueryStatus: null,
  companyQueryResults: [],
  companyBrowseItems: [],
  companyQuerySource: 'xlsx',
  companyQueryLastQuery: '',
  industryChainStatus: null,
  industryChainResult: null,
  industryChainMode: 'overview',
  industryChainScope: 'external_company',
  industryChainInputValues: {},
  industryChainSelectedTrackId: '',
  industryChainExpandedStages: new Set(),
  industryChainExpandedTracks: new Set(),
  industryChainAllExpanded: false,
  industryChainNetwork: null,
  industryChainNetworkGraph: null,
  industryChainNetworkKey: '',
  industryChainNetworkRequested: false,
  industryChainRelationVisibleCount: 10,
  industryChainOverviewCache: null,
  industryChainAutoReportRequested: false,
  industryChainRunStatus: null,
  competitiveStatus: null,
  competitiveReports: [],
  competitiveReport: null,
  competitiveSettings: null,
  competitiveJob: null,
  selectedNoteDate: null,
  noteCalendarCursor: null,
  sortModes: {
    policy: 'default',
    macro: 'default',
    industryFocus: 'default',
    target: 'default',
  },
};

const DAILY_NOTE_STORAGE_KEY = 'ceo-brief-daily-notes-v1';
const COMPANY_QUERY_HISTORY_KEY = 'ceo-brief-company-query-history-v1';
const COMPANY_QUERY_HISTORY_LIMIT = 5;
const INDUSTRY_CHAIN_ALL_TRACKS = '__all__';
const INDUSTRY_CHAIN_OVERVIEW_CACHE_MS = 7 * 24 * 60 * 60 * 1000;
const INDUSTRY_CHAIN_ANALYSIS_POLL_MS = 1200;
const INDUSTRY_CHAIN_ANALYSIS_MAX_POLLS = 90;
let industryChainRenderTimer = null;
let industryChainRunTimer = null;

const $ = (id) => document.getElementById(id);
const setText = (id, value) => {
  const el = $(id);
  if (el) el.textContent = value;
  return el;
};
const bindClick = (id, loadingText, fn) => {
  const el = $(id);
  if (!el) return;
  el.addEventListener('click', setLoading(el, loadingText, fn));
};
const bindDynamicLoadingClick = (id, loadingTextFn, fn) => {
  const el = $(id);
  if (!el) return;
  el.addEventListener('click', setLoading(el, loadingTextFn, fn));
};

function showMessage(text, type = 'success') {
  const el = $('globalMessage');
  if (!el) return;
  if (!text) {
    el.className = 'message hidden';
    el.textContent = '';
    return;
  }
  el.textContent = text;
  el.className = `message ${type}`;
  clearTimeout(showMessage._timer);
  showMessage._timer = setTimeout(() => {
    el.className = 'message hidden';
    el.textContent = '';
  }, 5000);
}

function setIndustryChainRunStatus(status) {
  state.industryChainRunStatus = status;
  if (industryChainRunTimer) {
    clearInterval(industryChainRunTimer);
    industryChainRunTimer = null;
  }
  if (status?.running) {
    industryChainRunTimer = setInterval(() => renderIndustryChain({ skipNetwork: true }), 1000);
  }
  renderIndustryChain({ skipNetwork: true });
}

function installRuntimeDiagnostics() {
  window.addEventListener('error', (event) => {
    const msg = event?.error?.message || event?.message || '未知前端错误';
    showMessage(`前端脚本异常: ${msg}`, 'error');
  });
  window.addEventListener('unhandledrejection', (event) => {
    const reason = event?.reason;
    const msg = reason?.message || String(reason || '未知异步错误');
    showMessage(`前端异步异常: ${msg}`, 'error');
  });
}

function apiUrl(path) {
  if (!path || /^https?:\/\//i.test(path)) return path;
  const apiPath = path.startsWith('/') ? path : `/${path}`;
  const configuredBase = String(window.__CEO_BRIEF_API_BASE__ || '').replace(/\/+$/, '');
  if (configuredBase) return `${configuredBase}${apiPath}`;
  const protocol = window.location.protocol;
  const host = window.location.hostname || '127.0.0.1';
  const isBackendOrigin = protocol.startsWith('http') && ['8000', '8001'].includes(window.location.port);
  if (isBackendOrigin) return apiPath;
  return `http://${host}:8001${apiPath}`;
}

function escapeHtml(value) {
  return String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}

function stripHtml(value) {
  const tmp = document.createElement('div');
  tmp.innerHTML = value || '';
  return tmp.textContent || tmp.innerText || '';
}

function safeFileName(value) {
  return String(value || 'report')
    .trim()
    .replace(/[\\/:*?"<>|]+/g, '-')
    .replace(/\s+/g, '-')
    .replace(/-+/g, '-')
    .slice(0, 80) || 'report';
}

function cleanSourceName(value) {
  return String(value || '').replace(/^RSSHub\s+/i, '').trim() || '未知来源';
}

function formatDateKey(date) {
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, '0');
  const d = String(date.getDate()).padStart(2, '0');
  return `${y}-${m}-${d}`;
}

function loadDailyNotes() {
  try {
    return JSON.parse(localStorage.getItem(DAILY_NOTE_STORAGE_KEY) || '{}');
  } catch {
    return {};
  }
}

function loadCompanyQueryHistory() {
  try {
    const data = JSON.parse(localStorage.getItem(COMPANY_QUERY_HISTORY_KEY) || '[]');
    return Array.isArray(data) ? data.filter((x) => typeof x === 'string' && x.trim()) : [];
  } catch {
    return [];
  }
}

function saveCompanyQueryHistory(history) {
  localStorage.setItem(COMPANY_QUERY_HISTORY_KEY, JSON.stringify(history.slice(0, COMPANY_QUERY_HISTORY_LIMIT)));
}

function pushCompanyQueryHistory(query) {
  const value = String(query || '').trim();
  if (!value) return;
  const history = loadCompanyQueryHistory().filter((item) => item !== value);
  history.unshift(value);
  saveCompanyQueryHistory(history);
}

function renderCompanyQueryHistory() {
  const wrap = $('companyQueryHistory');
  if (!wrap) return;
  const history = loadCompanyQueryHistory();
  if (!history.length) {
    wrap.className = 'company-query-chips empty';
    wrap.innerHTML = '<span class="muted small-meta">暂无历史查询</span>';
    return;
  }
  wrap.className = 'company-query-chips';
  wrap.innerHTML = history.map((item) => `
    <button class="secondary small-btn" type="button" data-company-query-history="${escapeHtml(item)}">${escapeHtml(item)}</button>
  `).join('');
}

function saveDailyNotes(notes) {
  localStorage.setItem(DAILY_NOTE_STORAGE_KEY, JSON.stringify(notes));
}

function getSelectedNoteText() {
  const notes = loadDailyNotes();
  return notes[state.selectedNoteDate || ''] || '';
}

function renderDailyNoteEditor() {
  const input = $('dailyNoteInput');
  if (input) input.value = getSelectedNoteText();
  setText('selectedNoteDate', state.selectedNoteDate || '-');
}

function saveSelectedNote() {
  if (!state.selectedNoteDate) return;
  const input = $('dailyNoteInput');
  if (!input) return;
  const notes = loadDailyNotes();
  const value = String(input.value || '').trim();
  if (value) notes[state.selectedNoteDate] = value;
  else delete notes[state.selectedNoteDate];
  saveDailyNotes(notes);
  renderCalendar();
  showMessage(`已保存 ${state.selectedNoteDate} 的记录`);
}

function renderCalendar() {
  const grid = $('calendarGrid');
  if (!grid) return;
  const base = state.noteCalendarCursor || new Date();
  const year = base.getFullYear();
  const month = base.getMonth();
  const firstDay = new Date(year, month, 1);
  const startOffset = (firstDay.getDay() + 6) % 7;
  const startDate = new Date(year, month, 1 - startOffset);
  const notes = loadDailyNotes();
  setText('calendarTitle', `${year}年${String(month + 1).padStart(2, '0')}月`);
  grid.innerHTML = Array.from({ length: 42 }).map((_, i) => {
    const d = new Date(startDate);
    d.setDate(startDate.getDate() + i);
    const key = formatDateKey(d);
    const todayKey = formatDateKey(new Date());
    const preview = notes[key] ? escapeHtml(String(notes[key]).split(/\r?\n/)[0].slice(0, 22)) : '';
    const classes = [
      'cal-day',
      d.getMonth() !== month ? 'is-other-month' : '',
      key === state.selectedNoteDate ? 'is-selected' : '',
      key === todayKey ? 'is-today' : '',
      notes[key] ? 'has-note' : '',
    ].filter(Boolean).join(' ');
    return `
      <button class="${classes}" data-note-date="${key}" type="button">
        <span class="cal-day-num">${d.getDate()}</span>
        ${preview ? `<span class="cal-day-preview">${preview}</span>` : ''}
      </button>
    `;
  }).join('');

  grid.querySelectorAll('[data-note-date]').forEach((el) => {
    el.addEventListener('click', () => {
      state.selectedNoteDate = el.dataset.noteDate;
      renderDailyNoteEditor();
      renderCalendar();
    });
  });
}

function deleteSelectedNote() {
  if (!state.selectedNoteDate) return;
  if (!confirm(`删除 ${state.selectedNoteDate} 的记录?`)) return;
  const notes = loadDailyNotes();
  delete notes[state.selectedNoteDate];
  saveDailyNotes(notes);
  const input = $('dailyNoteInput');
  if (input) input.value = '';
  renderCalendar();
  showMessage(`已删除 ${state.selectedNoteDate} 的记录`);
}

function handleNewsCardImageError(img) {
  const card = img?.closest('.news-tile');
  const media = img?.closest('.news-tile-media');
  if (media) media.remove();
  if (!card) return;
  card.classList.remove('has-media');
  card.classList.add('text-only', 'image-failed');
  const bodyTitle = card.querySelector('.body-title');
  if (bodyTitle) bodyTitle.style.display = 'block';
}

function renderNewsCard(item, options = {}) {
  const summary = escapeHtml(stripHtml(item.summary || ''));
  const imageUrl = item.imageUrl ? escapeHtml(item.imageUrl) : '';
  const source = escapeHtml(cleanSourceName(item.source));
  const publishedAt = escapeHtml(item.publishedAt || '');
  const relevance = options.showRelevance && item.relevanceScore != null
    ? `<span>相关度 ${escapeHtml(item.relevanceScore)}</span>`
    : '';
  const filteredTags = Array.isArray(item.matchedTargets)
    ? item.matchedTargets.filter((tag) => options.tagFilter ? options.tagFilter(tag, item) : true)
    : [];
  const tags = options.showTags && filteredTags.length
    ? `<div class="tags">${filteredTags.slice(0, 3).map((tag) => `<span class="tag">${escapeHtml(tag)}</span>`).join('')}</div>`
    : '';
  const reason = options.reasonLabel && item.relevanceReason
    ? `<div class="card-summary card-reason">${escapeHtml(options.reasonLabel)}:${escapeHtml(item.relevanceReason)}</div>`
    : '';
  const compactMeta = [source, publishedAt].filter(Boolean).join(' · ');
  const heroMeta = [source, publishedAt].filter(Boolean).join('  ·  ');
  const cardClass = options.featured ? 'news-tile is-featured' : 'news-tile';

  const mediaBlock = imageUrl
    ? `
        <div class="news-tile-media">
          <img src="${imageUrl}" alt="${escapeHtml(item.title || 'news image')}" loading="lazy" onerror="window.handleNewsCardImageError && window.handleNewsCardImageError(this)" />
          <div class="news-tile-overlay">
            <div class="news-tile-kicker">${heroMeta || '新闻卡片'}</div>
            <div class="news-tile-title">${escapeHtml(item.title)}</div>
          </div>
        </div>
      `
    : `
        <div class="news-tile-body no-media">
          <div class="news-tile-kicker inline-kicker">${heroMeta || '新闻卡片'}</div>
          <div class="news-tile-title inline-title">${escapeHtml(item.title)}</div>
          <div class="card-meta compact">
            <span>${compactMeta || '未知来源'}</span>
            ${relevance}
          </div>
          <div class="card-summary">${summary || '暂无摘要'}</div>
          ${tags}
          ${reason}
        </div>
      `;

  return `
    <article class="${cardClass} ${imageUrl ? 'has-media' : 'text-only'}">
      <a class="news-tile-link" href="${escapeHtml(item.url || '#')}" target="_blank" rel="noreferrer noopener">
        ${mediaBlock}
        ${imageUrl ? `
        <div class="news-tile-body">
          <div class="news-tile-title inline-title body-title" style="display:none">${escapeHtml(item.title)}</div>
          <div class="card-meta compact">
            <span>${compactMeta || '未知来源'}</span>
            ${relevance}
          </div>
          <div class="card-summary">${summary || '暂无摘要'}</div>
          ${tags}
          ${reason}
        </div>` : ''}
      </a>
    </article>
  `;
}

function sortNewsItems(items, mode) {
  const list = Array.isArray(items) ? [...items] : [];
  if (mode === 'latest') {
    return list.sort((a, b) => String(b.publishedAt || '').localeCompare(String(a.publishedAt || '')));
  }
  if (mode === 'relevance') {
    return list.sort((a, b) => Number(b.relevanceScore ?? -Infinity) - Number(a.relevanceScore ?? -Infinity));
  }
  return list;
}

function renderReaderList(items, options = {}) {
  let list = sortNewsItems(items, options.sortMode);
  if (options.preferImageFirst && list.length > 1 && !list[0]?.imageUrl) {
    const withImageIndex = list.findIndex((item) => item?.imageUrl);
    if (withImageIndex > 0) {
      const [picked] = list.splice(withImageIndex, 1);
      list = [picked, ...list];
    }
  }
  if (!list.length) return '';
  try {
    const [first, ...rest] = list;
    const featured = renderNewsCard(first, { ...options, featured: true });
    const masonry = rest.map((item) => renderNewsCard(item, options)).join('');
    return `
      <div class="reader-featured-wrap">${featured}</div>
      ${rest.length ? `<div class="reader-list-grid">${masonry}</div>` : ''}
    `;
  } catch (error) {
    console.error('renderReaderList failed', error);
    return list.map((item) => `
      <div class="card-item">
        <h4>${escapeHtml(item?.title || '-')}</h4>
        <div class="card-meta compact">
          <span>${escapeHtml(cleanSourceName(item?.source || '-'))}</span>
          <span>${escapeHtml(item?.publishedAt || '')}</span>
        </div>
        ${item?.summary ? `<div class="card-summary">${escapeHtml(stripHtml(item.summary))}</div>` : ''}
      </div>
    `).join('');
  }
}

async function api(path, options = {}) {
  const url = apiUrl(path);
  let res;
  try {
    res = await fetch(url, {
      headers: { 'Content-Type': 'application/json' },
      ...options,
    });
  } catch (error) {
    throw new Error(`无法连接后端接口 ${url}：${error?.message || '网络请求失败'}`);
  }
  const text = await res.text();
  let data = null;
  if (text) {
    try {
      data = JSON.parse(text);
    } catch (error) {
      data = { message: text.trim() || `${res.status} ${res.statusText}` };
    }
  }
  if (!res.ok) {
    throw new Error(data?.detail || data?.message || `${res.status} ${res.statusText}`);
  }
  return data;
}

function formatMarketNumber(value) {
  if (value == null || Number.isNaN(Number(value))) return '-';
  const num = Number(value);
  return Math.abs(num) >= 1000 ? num.toLocaleString('zh-CN', { maximumFractionDigits: 2 }) : num.toFixed(2);
}

function formatMarketPercent(value) {
  if (value == null || Number.isNaN(Number(value))) return '-';
  const num = Number(value);
  return `${num > 0 ? '+' : ''}${num.toFixed(2)}%`;
}

function renderMarketSnapshot() {
  const marketTrack = $('marketSliderTrack');
  const fxTrack = $('fxSliderTrack');
  const snapshot = state.marketSnapshot;
  const items = Array.isArray(snapshot?.items) ? snapshot.items : [];
  const fxNames = new Set(['USD/CNY', 'USD/JPY', 'EUR/USD', 'GBP/USD']);
  const marketItems = items.filter((item) => !fxNames.has(item.name));
  const fxItems = items.filter((item) => fxNames.has(item.name));

  setText('marketUpdatedAt', snapshot?.loading ? '行情加载中...' : (snapshot?.updatedAt ? `更新于 ${snapshot.updatedAt}` : '-'));

  const renderTrack = (track, list) => {
    if (!track) return;
    if (snapshot?.loading && !list.length) {
      track.textContent = '加载中...';
      return;
    }
    if (!list.length) {
      track.textContent = '暂无内容';
      return;
    }
    const slides = list.map((item) => {
      const percent = Number(item.changePercent ?? 0);
      const tone = percent > 0 ? 'up' : percent < 0 ? 'down' : 'flat';
      const change = item.change == null || Number.isNaN(Number(item.change))
        ? '-'
        : `${Number(item.change) > 0 ? '+' : ''}${formatMarketNumber(item.change)}`;
      return `
        <div class="slider-slide market-item ${tone}">
          <div class="market-item-head">
            <span class="market-name">${escapeHtml(item.name || item.symbol || '-')}</span>
            <span class="market-state">${escapeHtml(item.marketState || '')}</span>
          </div>
          <div class="market-price">${escapeHtml(formatMarketNumber(item.price))}</div>
          <div class="market-change">${escapeHtml(change)} · ${escapeHtml(formatMarketPercent(item.changePercent))}</div>
        </div>
      `;
    }).join('');
    track.innerHTML = slides + slides; // duplicate for seamless loop
  };

  renderTrack(marketTrack, marketItems);
  renderTrack(fxTrack, fxItems);
}

function renderHealth() {
}

function renderDeepSeekBudget(balance) {
  const fillEl = $('deepseekBudgetFill');
  const metaEl = $('deepseekBudgetMeta');
  const limit = Number(balance?.dailyLimitCny) || 5;
  const used = Number(balance?.usedCny);
  const percent = Number.isFinite(Number(balance?.usedPercent))
    ? Number(balance.usedPercent)
    : Number.isFinite(used)
      ? Math.max(0, Math.min(100, (used / limit) * 100))
      : 0;
  if (fillEl) fillEl.style.width = `${Math.max(0, Math.min(100, percent))}%`;
  if (!balance?.ok) {
    if (metaEl) metaEl.textContent = balance?.message || '读取失败';
    return;
  }
  if (metaEl) {
    const totalTokens = Number(balance?.totalTokens) || 0;
    const requestCount = Number(balance?.requestCount) || 0;
    const usageText = totalTokens > 0
      ? ` · ${requestCount}次 · ${totalTokens.toLocaleString('zh-CN')} tokens`
      : '';
    metaEl.textContent = balance?.limited ? `今日已达上限${usageText}` : `今日已用 ${Math.round(percent)}%${usageText}`;
  }
}

function setLoading(button, loadingText, fn) {
  return async () => {
    const old = button.textContent;
    const nextText = typeof loadingText === 'function' ? loadingText() : loadingText;
    button.disabled = true;
    button.textContent = nextText;
    try {
      await fn();
    } catch (error) {
      showMessage(error?.message || '操作失败', 'error');
      throw error;
    } finally {
      button.disabled = false;
      syncIndustryChainControls();
      if (button.isConnected && button.textContent === nextText) {
        button.textContent = old;
      }
    }
  };
}

function renderToday() {
  try {
    const data = state.today || {};
    const meta = data.meta || {};
    const llmSummaryEl = $('llmSummary');
    if (llmSummaryEl) {
      const llmSummary = String(data.llmSummary || '').trim();
      llmSummaryEl.textContent = llmSummary || '暂无内容';
      llmSummaryEl.className = llmSummary ? 'markdown-block' : 'markdown-block empty';
    }

    const weather = data.weather;
    const weatherEl = $('weatherBlock');
    if (weatherEl) {
      weatherEl.className = weather ? 'weather-inline' : 'weather-inline empty';
      weatherEl.innerHTML = weather
        ? `
          <span class="weather-inline-main">${escapeHtml(weather.location || '未知地点')} · ${escapeHtml(weather.condition || '-')}</span>
          <span class="weather-chip">${escapeHtml(weather.temperatureMin ?? '-')}° ~ ${escapeHtml(weather.temperatureMax ?? '-')}°</span>
          ${weather.advice ? `<span class="weather-chip">${escapeHtml(weather.advice)}</span>` : ''}
        `
        : '暂无内容';
    }

    renderNewsList('policyList', 'policyCount', data.policyNews, (items) => renderReaderList(items, {
      sortMode: state.sortModes.policy,
    }));

    renderNewsList('macroList', 'macroCount', data.macroEconomicNews, (items) => renderReaderList(items, {
      sortMode: state.sortModes.macro,
    }));

    renderNewsList('industryFocusList', 'industryFocusCount', data.industryFocusNews, (items) => renderReaderList(items, {
      sortMode: state.sortModes.industryFocus,
      showRelevance: true,
      showTags: true,
      reasonLabel: '命中依据',
    }));

    renderNewsList('targetList', 'targetCount', data.targetUpdates, (items) => renderReaderList(items, {
      sortMode: state.sortModes.target,
      showTags: true,
      preferImageFirst: true,
      tagFilter: (tag) => !['客户动态', '竞争对手动态', '目标', '行业机会', '中科天塔动态'].includes(tag),
    }));

    if (!state.selectedNoteDate) {
      state.selectedNoteDate = data.date || formatDateKey(new Date());
    }
    if (!state.noteCalendarCursor) {
      const baseDate = state.selectedNoteDate ? new Date(`${state.selectedNoteDate}T00:00:00`) : new Date();
      state.noteCalendarCursor = new Date(baseDate.getFullYear(), baseDate.getMonth(), 1);
    }
    renderDailyNoteEditor();
    renderCalendar();
  } catch (error) {
    console.error('renderToday failed', error);
    showMessage(`首页渲染失败: ${error.message}`, 'error');
  }
}

function renderNewsList(containerId, countId, items, renderItem) {
  const list = Array.isArray(items) ? items : [];
  setText(countId, String(list.length));
  const container = $(containerId);
  if (!container) return;
  if (!list.length) {
    container.className = 'list reader-list empty';
    container.textContent = '暂无数据';
    return;
  }
  container.className = 'list reader-list';
  try {
    const html = renderItem(list);
    container.innerHTML = html || list.map((item) => `
      <div class="card-item">
        <h4>${escapeHtml(item?.title || item?.content || '-')}</h4>
        ${item?.summary ? `<div class="card-summary">${escapeHtml(stripHtml(item.summary))}</div>` : ''}
        ${item?.reason ? `<div class="card-summary">${escapeHtml(item.reason)}</div>` : ''}
      </div>
    `).join('');
  } catch (error) {
    console.error(`renderNewsList failed for ${containerId}`, error);
    container.innerHTML = list.map((item) => `
      <div class="card-item">
        <h4>${escapeHtml(item?.title || item?.content || '-')}</h4>
        ${item?.summary ? `<div class="card-summary">${escapeHtml(stripHtml(item.summary))}</div>` : ''}
        ${item?.reason ? `<div class="card-summary">${escapeHtml(item.reason)}</div>` : ''}
      </div>
    `).join('');
  }
}

function arrayToTextarea(arr) {
  return Array.isArray(arr) ? arr.join('\n') : '';
}

function textareaToArray(value) {
  return String(value || '')
    .split(/\r?\n/)
    .map((x) => x.trim())
    .filter(Boolean);
}

function renderSettings() {
  const targets = state.targets || {};
  const prompts = state.prompts || {};
  const targetsForm = $('targetsForm');
  if (targetsForm) {
    ['companies', 'industries', 'keywords', 'regions', 'competitors', 'upstreamDownstream', 'watchlist'].forEach((key) => {
      if (targetsForm.elements[key]) {
        targetsForm.elements[key].value = arrayToTextarea(targets[key]);
      }
    });
  }

  const promptsForm = $('promptsForm');
  if (promptsForm) {
    ['newsFilterPrompt', 'newsSummaryPrompt', 'todoPrompt'].forEach((key) => {
      if (promptsForm.elements[key]) {
        promptsForm.elements[key].value = prompts[key] || '';
      }
    });
  }
}

async function loadDashboard() {
  const [health, today, deepseekBalance] = await Promise.all([
    api('/health').catch(() => null),
    api('/api/ceo-brief/today').catch(() => null),
    api('/api/ceo-brief/llm/balance').catch((error) => ({ ok: false, message: error.message })),
  ]);

  renderHealth(health);
  renderDeepSeekBudget(deepseekBalance);
  state.today = today || {};
  renderToday();

  if (!state.marketSnapshot) {
    state.marketSnapshot = { items: [], updatedAt: null, loading: true };
    renderMarketSnapshot();
  }

  api('/api/ceo-brief/market-snapshot')
    .then((marketSnapshot) => {
      state.marketSnapshot = marketSnapshot;
      renderMarketSnapshot();
    })
    .catch(() => {
      if (!state.marketSnapshot?.items?.length) {
        state.marketSnapshot = { items: [], updatedAt: null, loading: false };
        renderMarketSnapshot();
      }
    });
}

async function loadSettings() {
  const [targets, prompts] = await Promise.all([
    api('/api/ceo-brief/settings/targets'),
    api('/api/ceo-brief/settings/prompts'),
  ]);
  state.targets = targets;
  state.prompts = prompts;
  renderSettings();
}

async function loadCompanyQueryStatus() {
  const [status, browse] = await Promise.all([
    api('/api/company-query/status'),
    api('/api/company-query/browse'),
  ]);
  state.companyQueryStatus = status;
  state.companyBrowseItems = Array.isArray(browse?.items) ? browse.items : [];
  renderCompanyQuery();
}

async function runCompanyQuerySearch(queryOverride = '') {
  const input = $('companyQueryInput');
  const sourceSelect = $('companyQuerySource');
  const source = String(sourceSelect?.value || state.companyQuerySource || 'xlsx');
  const query = String(queryOverride || input?.value || '').trim();
  if (!query) {
    showMessage('请先输入企业名称或关键词', 'error');
    return;
  }
  if (source !== 'xlsx') {
    showMessage(`当前输入源 ${source} 尚未接通，现阶段请使用 XLSX 企业库。`, 'error');
    return;
  }
  state.companyQuerySource = source;
  if (input) input.value = query;
  const result = await api('/api/company-query/search', {
    method: 'POST',
    body: JSON.stringify({ query, source }),
  });
  state.companyQueryResults = Array.isArray(result?.results) ? result.results : [];
  state.companyQueryStatus = { ...(result?.meta || {}), message: `检索完成：关键词“${query}”，命中 ${result?.meta?.matchedRows ?? result?.count ?? 0} 条，当前展示 ${result?.count ?? 0} 条。` };
  state.companyQueryLastQuery = query;
  pushCompanyQueryHistory(query);
  renderCompanyQueryHistory();
  renderCompanyQuery();
}

async function loadIndustryChainStatus() {
  const status = await api('/api/industry-chain/status');
  state.industryChainStatus = status;
  renderIndustryChain();
}

function industryChainModeLabel(mode) {
  return {
    overview: '产业链全景',
    'company-updown': '产业链上下游',
    opportunities: '产业链机会探索',
    'graph-qa': '图谱知识问答',
  }[mode] || mode;
}

function industryChainOpportunityScopeLabel(scope) {
  return {
    external_company: '公司合作探索',
    technology_scope: '技术领域相关被投企业',
    industry_direction: '融链延链探索',
    graph_fact_discovery: '图谱事实发现',
  }[scope] || '公司合作探索';
}

function industryChainOpportunityTargetLabel(scope) {
  return {
    external_company: '目标公司',
    technology_scope: '目标技术领域',
    industry_direction: '目标产业领域',
    graph_fact_discovery: '目标问题',
  }[scope] || '目标对象';
}

function currentIndustryChainMode() {
  return $('industryChainMode')?.value || state.industryChainMode || 'overview';
}

function currentIndustryChainScope() {
  return $('industryChainScope')?.value || state.industryChainScope || 'external_company';
}

function industryChainInputKey(mode = currentIndustryChainMode(), scope = currentIndustryChainScope()) {
  return mode === 'opportunities' ? `${mode}:${scope || 'external_company'}` : mode;
}

function rememberIndustryChainInput(mode = currentIndustryChainMode(), scope = currentIndustryChainScope()) {
  const input = $('industryChainInput');
  if (!input) return;
  state.industryChainInputValues[industryChainInputKey(mode, scope)] = input.value || '';
}

function restoreIndustryChainInput(mode = currentIndustryChainMode(), scope = currentIndustryChainScope()) {
  const input = $('industryChainInput');
  if (!input) return;
  input.value = state.industryChainInputValues[industryChainInputKey(mode, scope)] || '';
}

function isIndustryChainResultCurrent(result, mode) {
  if (!result) return false;
  if (!result.mode) return mode === 'overview';
  if (result.mode !== mode) return false;
  if (mode === 'opportunities') {
    const resultScope = result?.query?.opportunityMode || result?.query?.scopeType || 'external_company';
    return resultScope === currentIndustryChainScope();
  }
  return true;
}

function resetIndustryChainNetwork() {
  state.industryChainNetwork?.destroy?.();
  state.industryChainNetwork = null;
  state.industryChainNetworkGraph = null;
  state.industryChainNetworkKey = '';
}

function renderIndustryNetworkPlaceholder(message = '点击后渲染网络图') {
  const networkEl = $('industryChainNetwork');
  const networkMetaEl = $('industryChainNetworkMeta');
  if (networkMetaEl) networkMetaEl.textContent = '节点关系';
  if (!networkEl) return;
  networkEl.className = 'industry-chain-network empty network-placeholder';
  networkEl.innerHTML = `
    <div>${escapeHtml(message)}</div>
    <button id="industryChainShowNetworkBtn" class="secondary" type="button">显示图谱</button>
  `;
}

function scheduleIndustryChainRender(options = {}) {
  if (industryChainRenderTimer) {
    clearTimeout(industryChainRenderTimer);
  }
  industryChainRenderTimer = setTimeout(() => {
    industryChainRenderTimer = null;
    const schedule = window.requestIdleCallback || ((callback) => setTimeout(callback, 0));
    schedule(() => renderIndustryChain(options));
  }, 0);
}

function scheduleIndustryChainAnalysis(mode) {
  setTimeout(() => {
    runIndustryChainAnalysis(mode).catch((error) => {
      showMessage(error?.message || '产业链分析加载失败', 'error');
    });
  }, 0);
}

function syncIndustryChainControls() {
  const mode = currentIndustryChainMode();
  state.industryChainMode = mode;
  const input = $('industryChainInput');
  const questionInput = $('industryChainQuestion');
  const keywordWrap = $('industryChainKeywordWrap');
  const questionWrap = $('industryChainQuestionWrap');
  const questionSection = $('industryChainQuestionSection');
  const scopeWrap = $('industryChainScopeWrap');
  const scopeSelect = $('industryChainScope');
  const keywordLabel = keywordWrap?.querySelector('span');
  const confirmBtn = $('industryChainInputConfirmBtn');
  const controls = document.querySelector('.industry-chain-controls');
  if (controls) controls.classList.toggle('graph-qa-mode', mode === 'graph-qa');
  if (scopeWrap) scopeWrap.style.display = mode === 'opportunities' ? 'block' : 'none';
  if (keywordWrap) keywordWrap.style.display = mode === 'overview' ? 'none' : 'grid';
  if (questionWrap) questionWrap.style.display = mode === 'overview' || mode === 'graph-qa' ? 'none' : 'grid';
  if (questionSection) questionSection.classList.toggle('hidden', mode === 'overview' || mode === 'graph-qa');
  if (scopeSelect && mode === 'opportunities' && !['external_company', 'technology_scope', 'industry_direction'].includes(scopeSelect.value)) {
    scopeSelect.value = 'external_company';
  }
  const scopeValue = scopeSelect?.value || 'external_company';
  state.industryChainScope = scopeValue;
  setText('industryChainOpportunityTitle', industryChainOpportunityScopeLabel(scopeValue));
  if (keywordLabel) {
    keywordLabel.textContent = mode === 'graph-qa'
      ? '问题'
      : mode === 'opportunities'
      ? ({
        external_company: '目标公司',
        technology_scope: '目标技术领域',
        industry_direction: '目标产业领域',
      }[scopeValue] || '目标对象')
      : '目标公司';
  }
  if (input) {
    input.disabled = mode === 'overview';
    input.placeholder = mode === 'graph-qa'
      ? '输入图谱问题，例如：哪些被投企业涉及大模型？'
      : mode === 'company-updown'
      ? '输入企业名，例如：中科慧远视觉技术（洛阳）有限公司'
      : mode === 'opportunities'
        ? {
          external_company: '输入目标公司，例如：某产业公司、某医院、某被投企业',
          technology_scope: '输入目标技术领域，例如：储能、无人机巡检、光纤传感',
          industry_direction: '输入目标产业领域，例如：新型电力系统、智能电网、数据中心',
        }[scopeValue] || '输入目标公司 / 技术领域 / 产业领域'
        : '全景模式无需输入目标公司';
  }
  if (confirmBtn) {
    confirmBtn.textContent = mode === 'graph-qa'
      ? '提问'
      : mode === 'company-updown'
        ? '查询'
        : mode === 'opportunities'
          ? '探索机会'
          : '加载全景';
  }
  if (questionInput) {
    questionInput.placeholder = '可以根据已经分析的结果继续提问';
  }
}

async function runIndustryChainAnalysis(forceMode = '', questionOverride = '') {
  const mode = forceMode || $('industryChainMode')?.value || state.industryChainMode || 'overview';
  const refreshOverviewCache = forceMode === 'overview-refresh';
  const effectiveMode = refreshOverviewCache ? 'overview' : mode;
  state.industryChainMode = effectiveMode;
  const modeSelect = $('industryChainMode');
  if (modeSelect && modeSelect.value !== effectiveMode) {
    modeSelect.value = effectiveMode;
  }
  syncIndustryChainControls();
  const question = String(questionOverride || $('industryChainQuestion')?.value || '').trim();
  if (questionOverride && $('industryChainQuestion')) {
    $('industryChainQuestion').value = questionOverride;
  }
  const questionAnswerEl = $('industryChainQuestionAnswer');
  if (questionAnswerEl && !questionOverride) {
    questionAnswerEl.className = 'industry-chain-question-answer hidden';
    questionAnswerEl.innerHTML = '';
  }

  let result;
  try {
    if (effectiveMode === 'overview') {
      setIndustryChainRunStatus({
        running: true,
        startedAt: Date.now(),
        message: refreshOverviewCache ? '正在刷新产业链图谱概览...' : '正在读取产业链图谱概览...',
      });
      const now = Date.now();
      if (!refreshOverviewCache && state.industryChainOverviewCache && now - state.industryChainOverviewCache.loadedAt < INDUSTRY_CHAIN_OVERVIEW_CACHE_MS) {
        result = state.industryChainOverviewCache.result;
      } else {
        const query = new URLSearchParams({ includeAnalysis: 'false' });
        if (refreshOverviewCache) query.set('refresh', 'true');
        result = await api(`/api/industry-chain/overview?${query.toString()}`);
        state.industryChainOverviewCache = { loadedAt: now, result };
      }
    } else if (effectiveMode === 'company-updown') {
      const keyword = String($('industryChainInput')?.value || '').trim();
      if (!keyword) {
        showMessage('请输入企业名称', 'error');
        return;
      }
      setIndustryChainRunStatus({
        running: true,
        startedAt: Date.now(),
        message: `正在查询“${keyword}”的上下游关系...`,
      });
      result = await api('/api/industry-chain/company-updown', {
        method: 'POST',
        body: JSON.stringify({ enterpriseName: keyword, question, includeAnalysis: false, limit: 30 }),
      });
    } else if (effectiveMode === 'opportunities') {
      const opportunityMode = String($('industryChainScope')?.value || 'external_company');
      const scopeType = opportunityMode;
      const keyword = String($('industryChainInput')?.value || '').trim();
      if (!keyword) {
        showMessage('请输入外部公司、技术范围或产业方向', 'error');
        return;
      }
      setIndustryChainRunStatus({
        running: true,
        startedAt: Date.now(),
        message: `正在为“${keyword}”召回候选企业、排序证据并生成报告，通常在 1 分钟以内...`,
      });
      result = await api('/api/industry-chain/opportunities', {
        method: 'POST',
        body: JSON.stringify({ scopeType, opportunityMode, keyword, question, includeAnalysis: true, limit: 30 }),
      });
    } else if (effectiveMode === 'graph-qa') {
      const graphQuestion = String($('industryChainInput')?.value || '').trim();
      if (!graphQuestion) {
        showMessage('请输入图谱问题', 'error');
        return;
      }
      setIndustryChainRunStatus({
        running: true,
        startedAt: Date.now(),
        message: '正在检索 Neo4j 图谱并生成回答，通常在 1 分钟以内...',
      });
      result = await api('/api/industry-chain/graph-qa', {
        method: 'POST',
        body: JSON.stringify({ question: graphQuestion, includeAnalysis: true, limit: 30 }),
      });
    } else {
      showMessage(`暂不支持的产业链分析模式：${effectiveMode}`, 'error');
      return;
    }

    state.industryChainResult = result;
    state.industryChainRelationVisibleCount = 10;
    setIndustryChainRunStatus(null);
    renderIndustryChain();
    const elapsedText = result?.meta?.elapsedMs ? `，耗时 ${Math.round(result.meta.elapsedMs / 1000)} 秒` : '';
    showMessage(`产业链分析已完成：返回 ${result?.meta?.rowCount ?? 0} 条结果${elapsedText}`, 'success');
  } catch (error) {
    setIndustryChainRunStatus({
      running: false,
      error: true,
      message: `产业链分析失败：${error?.message || '请求异常'}`,
    });
    throw error;
  }
}

async function runIndustryChainQuestionAnalysis(questionOverride = '') {
  const existing = state.industryChainResult;
  const mode = currentIndustryChainMode();
  if (!existing || existing.mode !== mode) {
    await runIndustryChainAnalysis('', questionOverride);
    if (state.industryChainResult?.mode === mode) {
      await runIndustryChainQuestionAnalysis(questionOverride);
    }
    return;
  }
  const question = String(questionOverride || $('industryChainQuestion')?.value || '').trim();
  if (questionOverride && $('industryChainQuestion')) {
    $('industryChainQuestion').value = questionOverride;
  }
  const answerEl = $('industryChainQuestionAnswer');
  if (answerEl) {
    answerEl.className = 'industry-chain-question-answer';
    answerEl.innerHTML = '分析中...';
  }
  let job;
  try {
    job = await api('/api/industry-chain/analyze-result/jobs', {
      method: 'POST',
      body: JSON.stringify({
        mode,
        query: existing.query || {},
        rows: Array.isArray(existing.rows) ? existing.rows : [],
        question,
      }),
    });
  } catch (error) {
    if (answerEl) {
      answerEl.className = 'industry-chain-question-answer empty';
      answerEl.innerHTML = `分析提交失败：${escapeHtml(error?.message || 'DeepSeek 接口调用失败')}`;
    }
    throw error;
  }
  const analysis = await pollIndustryChainQuestionAnalysis(job.jobId, answerEl);
  state.industryChainResult = {
    ...existing,
    answer: analysis.answer || '',
    query: analysis.query || existing.query,
    meta: { ...(existing.meta || {}), analysis: analysis.meta || {} },
  };
  if (answerEl) {
    const llm = analysis.meta?.llm || {};
    const llmNotice = llm.error
      ? `<div class="industry-chain-llm-warning">DeepSeek 调用失败，以下为规则分析：${escapeHtml(llm.error)}</div>`
      : llm.enabled === false
        ? '<div class="industry-chain-llm-warning">DeepSeek 未启用，以下为规则分析。</div>'
        : '';
    answerEl.className = analysis.answer ? 'industry-chain-question-answer' : 'industry-chain-question-answer empty';
    answerEl.innerHTML = analysis.answer ? `${llmNotice}${renderIndustryChainReport(analysis.answer)}` : '暂无分析结果';
  }
}

async function pollIndustryChainQuestionAnalysis(jobId, answerEl) {
  if (!jobId) throw new Error('analysis_job_missing');
  for (let index = 0; index < INDUSTRY_CHAIN_ANALYSIS_MAX_POLLS; index += 1) {
    await new Promise((resolve) => setTimeout(resolve, INDUSTRY_CHAIN_ANALYSIS_POLL_MS));
    const job = await api(`/api/industry-chain/analyze-result/jobs/${encodeURIComponent(jobId)}`);
    if (job.status === 'done') return job.result || {};
    if (job.status === 'error') throw new Error(job.error || 'DeepSeek 分析失败');
    if (answerEl) {
      answerEl.className = 'industry-chain-question-answer';
      answerEl.innerHTML = `分析中...${index + 1}`;
    }
  }
  throw new Error('DeepSeek 分析超时');
}

function renderIndustryChainGraph(graph) {
  const nodes = Array.isArray(graph?.nodes) ? graph.nodes : [];
  const edges = Array.isArray(graph?.edges) ? graph.edges : [];
  if (!nodes.length && !edges.length) return '<div class="empty">暂无图谱</div>';
  if ((state.industryChainResult?.mode || state.industryChainMode) === 'company-updown') {
    return renderCompanyUpdownTree(state.industryChainResult);
  }
  const tree = buildIndustryChainTree(nodes, edges);
  if (tree) return renderIndustryChainTree(tree, graph);
  const visibleNodes = nodes.filter((node) => node.type !== 'Enterprise').slice(0, 40);
  return `
    <div class="industry-chain-node-cloud">
      ${visibleNodes.map((node) => `
        <span class="industry-chain-node node-${escapeHtml(node.type || 'unknown')}">
          <span class="industry-chain-node-type">${escapeHtml(node.groupLabel || node.type || '-')}</span>
          ${escapeHtml(node.label || node.id || '-')}
        </span>
      `).join('')}
    </div>
  `;
}

function renderCompanyUpdownTree(result) {
  const rows = Array.isArray(result?.rows) ? result.rows : [];
  if (!rows.length) return '<div class="industry-chain-tree-empty">未找到该企业的上下游关系</div>';
  return `
    <div class="industry-updown-view">
      ${rows.map((row) => {
        const enterprise = row.enterprise || result?.query?.enterpriseName || '-';
        const stages = _asArray(row.stages).filter(Boolean);
        const subTracks = _asArray(row.subTracks).filter(Boolean);
        const capabilities = _asArray(row.keyCapabilities).filter(Boolean);
        const upstreamGroups = buildCompanyUpdownGroups(row, 'upstream', enterprise);
        const downstreamGroups = buildCompanyUpdownGroups(row, 'downstream', enterprise);
        return `
          <section class="industry-updown-card">
            <div class="industry-updown-card-head">
              <div>
                <b>${escapeHtml(enterprise)}</b>
                <span>${escapeHtml(subTracks.join(' / ') || '未标注产业链')}</span>
              </div>
              <em>${escapeHtml(row.matchLevel || '企业上下游')}</em>
            </div>
            <div class="industry-updown-meta">
              <span>所在环节：${escapeHtml(stages.join('、') || '-')}</span>
              ${capabilities.length ? `<span>关键能力：${escapeHtml(capabilities.slice(0, 6).join('、'))}</span>` : ''}
            </div>
            <div class="industry-updown-tree">
              ${renderCompanyUpdownBranch('上游', upstreamGroups, 'upstream')}
              <div class="industry-updown-trunk">
                <div class="industry-updown-target">
                  <span>目标企业</span>
                  <b>${escapeHtml(enterprise)}</b>
                  <em>${escapeHtml(stages.join('、') || '未标注环节')}</em>
                </div>
              </div>
              ${renderCompanyUpdownBranch('下游', downstreamGroups, 'downstream')}
            </div>
          </section>
        `;
      }).join('')}
    </div>
  `;
}

function buildCompanyUpdownGroups(row, direction, targetEnterprise) {
  const relationKey = direction === 'upstream' ? 'upstreamRelations' : 'downstreamRelations';
  const stageKey = direction === 'upstream' ? 'upstreamStages' : 'downstreamStages';
  const enterpriseKey = direction === 'upstream' ? 'upstreamEnterprises' : 'downstreamEnterprises';
  const groups = new Map();
  _asArray(row[relationKey]).forEach((item) => {
    if (!item || typeof item !== 'object') return;
    const stage = String(item.stage || '').trim();
    const enterprise = String(item.enterprise || '').trim();
    if (!stage || !enterprise || enterprise === targetEnterprise) return;
    const list = groups.get(stage) || [];
    if (!list.includes(enterprise)) list.push(enterprise);
    groups.set(stage, list);
  });
  if (!groups.size) {
    const fallbackStage = _asArray(row[stageKey]).filter(Boolean).join('、') || '未标注环节';
    const enterprises = _asArray(row[enterpriseKey]).filter((name) => name && name !== targetEnterprise);
    if (enterprises.length) groups.set(fallbackStage, [...new Set(enterprises)]);
  }
  return [...groups.entries()].map(([stage, enterprises]) => ({ stage, enterprises }));
}

function renderCompanyUpdownBranch(title, groups, direction) {
  const total = groups.reduce((sum, group) => sum + group.enterprises.length, 0);
  return `
    <div class="industry-updown-branch ${escapeHtml(direction)}">
      <div class="industry-updown-branch-title">${escapeHtml(title)} <span>${escapeHtml(total)} 家</span></div>
      <div class="industry-updown-stage-list">
        ${groups.length ? groups.map((group) => renderCompanyUpdownStage(group, direction)).join('') : '<i class="industry-updown-empty">暂无关联企业</i>'}
      </div>
    </div>
  `;
}

function renderCompanyUpdownStage(group, direction) {
  return `
    <section class="industry-updown-stage ${escapeHtml(direction)}">
      <div class="industry-updown-stage-node">
        <span>环节</span>
        <b>${escapeHtml(group.stage || '-')}</b>
      </div>
      <div class="industry-updown-company-nodes">
        ${group.enterprises.map((name) => `
          <button type="button" class="industry-updown-company-node" data-industry-company="${escapeHtml(name)}">${escapeHtml(name)}</button>
        `).join('')}
      </div>
    </section>
  `;
}

function buildIndustryChainTree(nodes, edges) {
  const byId = new Map(nodes.map((node) => [node.id, node]));
  const subTracks = nodes.filter((node) => node.type === 'SubTrack');
  if (!subTracks.length) return null;
  const stageBySubTrack = new Map();
  const enterpriseByStage = new Map();
  edges.forEach((edge) => {
    if (edge.type === 'HAS_STAGE') {
      const source = byId.get(edge.source);
      const target = byId.get(edge.target);
      if (source?.type === 'SubTrack' && target?.type === 'ChainStage') {
        const list = stageBySubTrack.get(source.id) || [];
        list.push(target);
        stageBySubTrack.set(source.id, list);
      }
    }
    if (edge.type === 'LOCATED_IN_STAGE') {
      const source = byId.get(edge.source);
      const target = byId.get(edge.target);
      if (source?.type === 'Enterprise' && target?.type === 'ChainStage') {
        const list = enterpriseByStage.get(target.id) || [];
        list.push(source);
        enterpriseByStage.set(target.id, list);
      }
    }
  });
  const tracks = subTracks.map((subTrack) => {
    const stages = (stageBySubTrack.get(subTrack.id) || [])
      .sort((a, b) => (Number(a.properties?.stageOrder) || 999) - (Number(b.properties?.stageOrder) || 999))
      .map((stage) => ({
        ...stage,
        enterprises: enterpriseByStage.get(stage.id) || [],
      }));
    return { ...subTrack, stages };
  }).filter((item) => item.stages.length);
  if (!tracks.length) return null;
  return {
    label: '产业链全景',
    trackCount: tracks.length,
    stageCount: tracks.reduce((sum, track) => sum + track.stages.length, 0),
    tracks,
  };
}

function renderIndustryChainTree(tree) {
  const tracks = Array.isArray(tree?.tracks) ? tree.tracks : [];
  if (!tracks.length) return '<div class="industry-chain-tree-empty">暂无树状图数据</div>';
  if (state.industryChainSelectedTrackId === INDUSTRY_CHAIN_ALL_TRACKS) {
    return renderIndustryChainAllTracksTree(tree, tracks);
  }
  const selectedTrack = getSelectedIndustryTrack(tracks);
  if (!selectedTrack) return '<div class="industry-chain-tree-empty">请选择一条产业链</div>';
  const levels = ['上游', '中游', '下游'];
  const levelGroups = levels.map((level) => ({
    level,
    stages: selectedTrack.stages.filter((stage) => normalizeStageLevel(stage.properties?.stageLevel) === level),
  }));
  const otherStages = selectedTrack.stages.filter((stage) => !levels.includes(normalizeStageLevel(stage.properties?.stageLevel)));
  if (otherStages.length) levelGroups.push({ level: '其他', stages: otherStages });
  return `
    <div class="industry-chain-tree">
      <div class="industry-chain-tree-summary">
        <div>
          <b>${escapeHtml(selectedTrack.label || '-')}</b>
          <span>${escapeHtml(selectedTrack.stages.length)} 个环节</span>
        </div>
        <p>${escapeHtml(selectedTrack.properties?.description || '点击环节展开查看挂载企业。')}</p>
      </div>
      <div class="industry-chain-tree-levels">
        ${levelGroups.map((group) => `
          <section class="industry-chain-tree-level">
            <div class="industry-chain-tree-level-title">${escapeHtml(group.level)}</div>
            <div class="industry-chain-tree-stages">
              ${group.stages.length ? group.stages.map((stage) => renderIndustryStageNode(stage)).join('') : '<div class="industry-chain-tree-empty">暂无环节</div>'}
            </div>
          </section>
        `).join('')}
      </div>
    </div>
  `;
}

function renderIndustryChainAllTracksTree(tree, tracks) {
  return `
    <div class="industry-chain-tree industry-chain-tree-all">
      <div class="industry-chain-tree-summary">
        <div>
          <b>产业链全貌</b>
          <span>${escapeHtml(tree.trackCount)} 条产业链 / ${escapeHtml(tree.stageCount)} 个环节</span>
        </div>
      </div>
      <div class="industry-chain-all-toolbar">
        <button class="secondary small-btn" type="button" data-industry-expand-all>${state.industryChainAllExpanded ? '全部折叠' : '全部展开'}</button>
      </div>
      <div class="industry-chain-all-tracks">
        ${tracks.map((track) => renderIndustryTrackBlock(track)).join('')}
      </div>
    </div>
  `;
}

function renderIndustryTrackBlock(track) {
  const expanded = state.industryChainAllExpanded || state.industryChainExpandedTracks.has(track.id);
  const levels = ['上游', '中游', '下游'];
  const levelGroups = levels.map((level) => ({
    level,
    stages: track.stages.filter((stage) => normalizeStageLevel(stage.properties?.stageLevel) === level),
  }));
  const otherStages = track.stages.filter((stage) => !levels.includes(normalizeStageLevel(stage.properties?.stageLevel)));
  if (otherStages.length) levelGroups.push({ level: '其他', stages: otherStages });
  return `
    <section class="industry-chain-all-track ${expanded ? 'expanded' : ''}">
      <button class="industry-chain-all-track-title" type="button" data-industry-track-id="${escapeHtml(track.id)}" aria-expanded="${expanded ? 'true' : 'false'}">
        <b>${escapeHtml(track.label || '-')}</b>
        <span>${escapeHtml(track.stages.length)} 个环节</span>
      </button>
      ${expanded ? `<div class="industry-chain-tree-levels">
        ${levelGroups.map((group) => `
          <section class="industry-chain-tree-level">
            <div class="industry-chain-tree-level-title">${escapeHtml(group.level)}</div>
            <div class="industry-chain-tree-stages">
              ${group.stages.length ? group.stages.map((stage) => renderIndustryStageNode(stage, { forceExpanded: state.industryChainAllExpanded, enterpriseLimit: 12 })).join('') : '<div class="industry-chain-tree-empty">暂无环节</div>'}
            </div>
          </section>
        `).join('')}
      </div>` : ''}
    </section>
  `;
}

function renderIndustryStageNode(stage, options = {}) {
  const enterprises = stage.enterprises || [];
  const enterpriseCount = Number(stage.properties?.enterpriseCount) || enterprises.length || 0;
  const expanded = options.forceExpanded || state.industryChainExpandedStages.has(stage.id);
  const enterpriseLimit = Number(options.enterpriseLimit) || enterprises.length;
  const visibleEnterprises = enterprises.slice(0, enterpriseLimit);
  const hiddenCount = Math.max(0, enterpriseCount - visibleEnterprises.length);
  return `
    <article class="industry-chain-tree-stage ${expanded ? 'expanded' : ''}" data-industry-stage-id="${escapeHtml(stage.id)}">
      <button class="industry-chain-tree-stage-toggle" type="button" data-industry-stage-id="${escapeHtml(stage.id)}" aria-expanded="${expanded ? 'true' : 'false'}">
        <span>${escapeHtml(stage.properties?.stageLevel || '环节')}</span>
        <b>${escapeHtml(stage.label || '-')}</b>
        <em>${escapeHtml(enterpriseCount)} 家</em>
      </button>
      ${expanded ? `
        <div class="industry-chain-tree-companies">
          ${visibleEnterprises.length ? visibleEnterprises.map((enterprise) => `
            <button class="industry-chain-tree-company" type="button" data-industry-company="${escapeHtml(enterprise.label || '')}">
              ${escapeHtml(enterprise.label || '-')}
            </button>
          `).join('') : '<i>暂无挂载企业</i>'}
          ${hiddenCount ? `<i>另有 ${escapeHtml(hiddenCount)} 家</i>` : ''}
        </div>
      ` : ''}
    </article>
  `;
}

function normalizeStageLevel(value) {
  const text = String(value || '').trim();
  if (text.includes('上')) return '上游';
  if (text.includes('中')) return '中游';
  if (text.includes('下')) return '下游';
  return text || '其他';
}

function getSelectedIndustryTrack(tracks) {
  const selectedId = state.industryChainSelectedTrackId;
  return tracks.find((track) => track.id === selectedId) || tracks[0] || null;
}

function updateIndustryChainTrackSelect(graph) {
  const select = $('industryChainTrackSelect');
  if (!select) return;
  const nodes = Array.isArray(graph?.nodes) ? graph.nodes : [];
  const edges = Array.isArray(graph?.edges) ? graph.edges : [];
  const tree = buildIndustryChainTree(nodes, edges);
  const tracks = Array.isArray(tree?.tracks) ? tree.tracks : [];
  if (!tracks.length) {
    select.innerHTML = '<option value="">暂无产业链</option>';
    select.disabled = true;
    state.industryChainSelectedTrackId = '';
    return;
  }
  const current = !state.industryChainSelectedTrackId
    ? INDUSTRY_CHAIN_ALL_TRACKS
    : state.industryChainSelectedTrackId === INDUSTRY_CHAIN_ALL_TRACKS
    ? INDUSTRY_CHAIN_ALL_TRACKS
    : tracks.some((track) => track.id === state.industryChainSelectedTrackId)
    ? state.industryChainSelectedTrackId
    : INDUSTRY_CHAIN_ALL_TRACKS;
  state.industryChainSelectedTrackId = current;
  select.disabled = false;
  select.innerHTML = `
    <option value="${INDUSTRY_CHAIN_ALL_TRACKS}" ${current === INDUSTRY_CHAIN_ALL_TRACKS ? 'selected' : ''}>产业链全貌</option>
    ${tracks.map((track) => `
    <option value="${escapeHtml(track.id)}" ${track.id === current ? 'selected' : ''}>${escapeHtml(track.label || '-')}</option>
  `).join('')}
  `;
}

function renderIndustryChainNetwork(graph) {
  const container = $('industryChainNetwork');
  if (!container) return;
  container.className = 'industry-chain-network';
  const metaEl = $('industryChainNetworkMeta');
  if (metaEl) {
    metaEl.textContent = state.industryChainSelectedTrackId === INDUSTRY_CHAIN_ALL_TRACKS ? '全部产业链节点关系' : '当前产业链节点关系';
  }
  if (!window.vis?.Network) {
    container.innerHTML = '<div class="empty">网络图组件未加载</div>';
    return;
  }
  const nodes = Array.isArray(graph?.nodes) ? graph.nodes : [];
  const edges = Array.isArray(graph?.edges) ? graph.edges : [];
  const selectedTrackId = state.industryChainSelectedTrackId;
  const visible = filterIndustryNetwork(nodes, edges, selectedTrackId);
  const graphKey = `${selectedTrackId || ''}|${visible.nodes.map((node) => node.id).join(',')}|${visible.edges.map((edge) => `${edge.source}>${edge.target}:${edge.type || ''}`).join(',')}`;
  if (state.industryChainNetwork && state.industryChainNetworkGraph === graph && state.industryChainNetworkKey === graphKey) {
    return;
  }
  if (!visible.nodes.length) {
    state.industryChainNetwork?.destroy?.();
    state.industryChainNetwork = null;
    state.industryChainNetworkGraph = null;
    state.industryChainNetworkKey = graphKey;
    container.innerHTML = '<div class="empty">暂无网络关系</div>';
    return;
  }
  const data = {
    nodes: new vis.DataSet(visible.nodes.map((node) => ({
      id: node.id,
      label: node.label || node.id,
      group: node.type || 'unknown',
      title: `${node.groupLabel || node.type || '-'}：${node.label || node.id}`,
      shape: node.type === 'Enterprise' ? 'dot' : 'box',
      value: node.type === 'Enterprise' ? 8 : 18,
    }))),
    edges: new vis.DataSet(visible.edges.map((edge) => ({
      from: edge.source,
      to: edge.target,
      label: edge.type === 'HAS_STAGE' ? '' : (edge.label || ''),
      arrows: 'to',
      color: { color: 'rgba(148, 163, 184, 0.45)' },
      font: { color: '#9fb4e8', size: 10, strokeWidth: 0 },
    }))),
  };
  const options = {
    autoResize: true,
    nodes: {
      borderWidth: 1,
      color: {
        border: 'rgba(148, 163, 184, 0.55)',
        background: 'rgba(91, 140, 255, 0.18)',
        highlight: { border: '#5b8cff', background: 'rgba(91, 140, 255, 0.32)' },
      },
      font: { color: '#ecf2ff', size: 12, face: 'Microsoft YaHei' },
      margin: 10,
    },
    groups: {
      SubTrack: { color: { background: 'rgba(91, 140, 255, 0.28)', border: '#5b8cff' }, shape: 'box' },
      ChainStage: { color: { background: 'rgba(16, 185, 129, 0.18)', border: '#10b981' }, shape: 'box' },
      Enterprise: { color: { background: 'rgba(245, 158, 11, 0.24)', border: '#f59e0b' }, shape: 'dot' },
    },
    edges: { smooth: { type: 'dynamic' } },
    physics: {
      stabilization: true,
      barnesHut: { gravitationalConstant: -4500, springLength: 130, springConstant: 0.04 },
    },
    interaction: { hover: true, tooltipDelay: 120, navigationButtons: true },
  };
  state.industryChainNetwork?.destroy?.();
  container.innerHTML = '';
  state.industryChainNetwork = new vis.Network(container, data, options);
  state.industryChainNetworkGraph = graph;
  state.industryChainNetworkKey = graphKey;
}

function filterIndustryNetwork(nodes, edges, trackId) {
  const byId = new Map(nodes.map((node) => [node.id, node]));
  if ((state.industryChainResult?.mode || state.industryChainMode) !== 'overview') {
    return {
      nodes: nodes.slice(0, 140),
      edges: edges.filter((edge) => byId.has(edge.source) && byId.has(edge.target)).slice(0, 220),
    };
  }
  if (trackId === INDUSTRY_CHAIN_ALL_TRACKS) {
    const stageIds = new Set(nodes.filter((node) => node.type === 'ChainStage').map((node) => node.id));
    const trackIds = new Set(nodes.filter((node) => node.type === 'SubTrack').map((node) => node.id));
    const enterpriseIds = new Set();
    edges.forEach((edge) => {
      if (edge.type === 'LOCATED_IN_STAGE' && stageIds.has(edge.target) && enterpriseIds.size < 160) {
        enterpriseIds.add(edge.source);
      }
    });
    const included = new Set([...trackIds, ...stageIds, ...enterpriseIds]);
    return {
      nodes: nodes.filter((node) => included.has(node.id)),
      edges: edges.filter((edge) => included.has(edge.source) && included.has(edge.target)),
    };
  }
  const included = new Set();
  if (trackId) included.add(trackId);
  edges.forEach((edge) => {
    if (edge.type === 'HAS_STAGE' && edge.source === trackId) {
      included.add(edge.target);
    }
  });
  let changed = true;
  while (changed) {
    changed = false;
    edges.forEach((edge) => {
      const sourceIncluded = included.has(edge.source);
      const targetIncluded = included.has(edge.target);
      if (edge.type === 'LOCATED_IN_STAGE' && targetIncluded && !sourceIncluded) {
        included.add(edge.source);
        changed = true;
      }
      if (edge.type === 'UPSTREAM_OF' && (sourceIncluded || targetIncluded)) {
        if (!sourceIncluded) included.add(edge.source);
        if (!targetIncluded) included.add(edge.target);
        changed = true;
      }
    });
  }
  const visibleNodes = nodes.filter((node) => included.has(node.id));
  const limitedEnterpriseIds = new Set(visibleNodes
    .filter((node) => node.type === 'Enterprise')
    .slice(0, 80)
    .map((node) => node.id));
  const limitedNodeIds = new Set(visibleNodes
    .filter((node) => node.type !== 'Enterprise')
    .map((node) => node.id));
  limitedEnterpriseIds.forEach((id) => limitedNodeIds.add(id));
  const visibleEdges = edges.filter((edge) => limitedNodeIds.has(edge.source) && limitedNodeIds.has(edge.target));
  return {
    nodes: Array.from(limitedNodeIds).map((id) => byId.get(id)).filter(Boolean),
    edges: visibleEdges,
  };
}

function industryChainStats(result) {
  const rows = Array.isArray(result?.rows) ? result.rows : [];
  const graphNodes = Array.isArray(result?.graph?.nodes) ? result.graph.nodes : [];
  const opportunities = Array.isArray(result?.opportunities) ? result.opportunities : [];
  const subTracks = new Set();
  const stages = new Set();
  const enterprises = new Set();
  let emptyStages = 0;
  rows.forEach((row) => {
    if (row.subTrack) subTracks.add(row.subTrack);
    if (row.stage || row.stageId) stages.add(row.stage || row.stageId);
    if ((Number(row.enterpriseCount) || 0) === 0 && (row.stage || row.stageId)) emptyStages += 1;
    _asArray(row.enterprises).forEach((name) => enterprises.add(name));
    if (row.enterprise) enterprises.add(row.enterprise);
    if (row.sourceEnterprise) enterprises.add(row.sourceEnterprise);
    if (row.targetEnterprise) enterprises.add(row.targetEnterprise);
  });
  graphNodes.forEach((node) => {
    if (node.type === 'SubTrack') subTracks.add(node.label || node.id);
    if (node.type === 'ChainStage') stages.add(node.label || node.id);
    if (node.type === 'Enterprise') enterprises.add(node.label || node.id);
  });
  opportunities.forEach((item) => {
    if (item.sourceEnterprise) enterprises.add(item.sourceEnterprise);
    if (item.targetEnterprise) enterprises.add(item.targetEnterprise);
    if (item.subTrack) subTracks.add(item.subTrack);
  });
  return {
    subTrackCount: subTracks.size,
    stageCount: stages.size,
    enterpriseCount: enterprises.size,
    rowCount: result?.meta?.rowCount ?? rows.length,
    emptyStages,
    opportunityCount: opportunities.length,
    highConfidenceCount: opportunities.filter((item) => item.confidence === 'high').length,
  };
}

function _asArray(value) {
  return Array.isArray(value) ? value : (value ? [value] : []);
}

function renderIndustryChainDashboard(result) {
  if (!result) return '<div class="empty">暂无图表</div>';
  const mode = result.mode || state.industryChainMode;
  if (mode === 'graph-qa') return '<div class="empty">图谱知识问答不显示图表总览</div>';
  const stats = industryChainStats(result);
  const opportunities = Array.isArray(result.opportunities) ? result.opportunities : [];
  const inventoryEnterpriseCount = Number(state.companyQueryStatus?.rowCount) || state.companyBrowseItems.length || 0;
  const cards = [
    ['产业链/子赛道', stats.subTrackCount],
    ['产业链环节', stats.stageCount],
    [mode === 'overview' ? '链上关联企业' : '关联企业', stats.enterpriseCount],
    [mode === 'opportunities' ? '合作机会' : '入库企业总数', mode === 'opportunities' ? stats.opportunityCount : inventoryEnterpriseCount],
  ];
  const detail = mode === 'opportunities' ? `
    <div class="industry-chain-visual-grid">
      <div class="industry-chain-chart">
        <div class="industry-chain-chart-title">合作机会矩阵</div>
        ${renderOpportunityMatrix(opportunities)}
      </div>
    </div>
  ` : '';
  return `
    <div class="industry-chain-kpis">
      ${cards.map(([label, value]) => `
        <div class="industry-chain-kpi">
          <span>${escapeHtml(label)}</span>
          <b>${escapeHtml(value)}</b>
        </div>
      `).join('')}
    </div>
    ${detail}
  `;
}

function renderStageBars(rows, maxCount) {
  if (!rows.length) return '<div class="empty">暂无环节分布数据</div>';
  return `
    <div class="industry-chain-bars">
      ${rows.map((row) => {
        const count = Number(row.enterpriseCount) || _asArray(row.enterprises).length || 0;
        const width = Math.max(6, Math.round((count / maxCount) * 100));
        return `
          <div class="industry-chain-bar-row">
            <span>${escapeHtml(row.stage || row.sourceStage || row.targetStage || '-')}</span>
            <div class="industry-chain-bar-track"><i style="width:${width}%"></i></div>
            <b>${escapeHtml(count)}</b>
          </div>
        `;
      }).join('')}
    </div>
  `;
}

function renderOpportunityMatrix(opportunities) {
  if (!opportunities.length) return '<div class="empty">暂无合作机会数据</div>';
  return `
    <div class="industry-chain-opportunity-list">
      ${opportunities.slice(0, 8).map((item) => `
        <div class="industry-chain-opportunity-row">
          <b>${escapeHtml(item.sourceEnterprise || '-')}</b>
          <span>${escapeHtml(cleanOpportunityText(item.opportunityTypeLabel || item.opportunityType || '合作'))}</span>
          <b>${escapeHtml(item.targetEnterprise || '-')}</b>
          <em>${escapeHtml(item.confidence || '-')}</em>
        </div>
      `).join('')}
    </div>
  `;
}

function renderOpportunityCards(result) {
  const opportunities = Array.isArray(result?.opportunities) ? result.opportunities : [];
  if (result?.answer) {
    const llm = result.meta?.llm || {};
    const llmNotice = llm.error
      ? `<div class="industry-chain-llm-warning">DeepSeek 调用失败，以下为规则分析：${escapeHtml(llm.error)}</div>`
      : llm.enabled === false
        ? '<div class="industry-chain-llm-warning">DeepSeek 未启用，以下为规则分析。</div>'
        : '';
    return `<div class="industry-chain-report">${llmNotice}${renderIndustryChainReport(result.answer, result)}</div>`;
  }
  if (!opportunities.length) return '<div class="empty">暂无合作机会</div>';
  return `
    <div class="industry-opportunity-card-list">
      ${opportunities.map((item) => renderOpportunityCard(item)).join('')}
    </div>
  `;
}

function renderExternalCompanyRag(result) {
  const profile = result?.externalProfile || null;
  const groups = Array.isArray(result?.groupedOpportunities) ? result.groupedOpportunities : [];
  if (!profile && !groups.length) return '';
  const profileSummary = profile ? buildCompactBusinessProfile(profile) : '';
  return `
    <section class="external-rag-block">
      ${profile ? `
        <div class="external-profile-card">
          <div class="external-profile-head">
            <span>目标公司画像</span>
            <b>${escapeHtml(profile.companyName || result?.query?.keyword || '目标公司')}</b>
          </div>
          <p class="external-profile-summary">${escapeHtml(profileSummary)}</p>
        </div>
      ` : ''}
      ${groups.length ? `
        <div class="external-dimension-grid">
          ${groups.map((group) => `
            <div class="external-dimension-card">
              <div class="external-dimension-head">
                <b>${escapeHtml(cleanOpportunityText(group.description || group.mode || '合作方向'))}</b>
                <em>${escapeHtml(group.count || 0)} 家可展示</em>
              </div>
              <p>${escapeHtml(_asArray(group.queryTerms).slice(0, 8).join('、') || '待核验')}</p>
            </div>
          `).join('')}
        </div>
      ` : ''}
    </section>
  `;
}

function buildCompactBusinessProfile(profile) {
  const products = _asArray(profile.coreProducts).concat(_asArray(profile.coreTechnologies)).slice(0, 8).join('、') || '规则画像未明确';
  const position = profile.chainPosition || '规则画像未明确';
  const needs = _asArray(profile.upstreamNeeds).slice(0, 5).join('、') || '待核验';
  const applications = _asArray(profile.downstreamApplications).concat(_asArray(profile.targetCustomers)).slice(0, 5).join('、') || '待核验';
  return `业务与位置：${position}；核心产品/技术：${products}。需求与场景：上游需求包括 ${needs}；下游应用/客户包括 ${applications}。`;
}

function industryChainFieldLabel(field) {
  return {
    products: '产品',
    capabilities: '能力',
    targetCapabilities: '能力/产品',
    scenarios: '场景',
    demands: '需求',
    customers: '客户',
    industries: '行业',
    subTrack: '产业链/赛道',
    targetStage: '环节',
    suppliers: '供应商',
  }[field] || field;
}

function buildOpportunityOneLine(item) {
  const enterprise = item.investedEnterprise || item.targetEnterprise || item.sourceEnterprise || '该企业';
  const direction = cleanOpportunityText(item.opportunityTypeLabel || item.matchedDimension || item.opportunityType || '合作');
  const domain = item.subTrack || item.scenario || _asArray(item.scenarios)[0] || item.targetStage || item.sourceStage || '';
  const capability = _asArray(item.targetCapabilities || item.products || item.capabilities)[0] || '';
  const focus = domain && capability
    ? `${domain}方向的${capability}`
    : domain || capability || '相关业务';
  return `${enterprise}可在${focus}上与目标公司开展${direction}。`;
}

function renderOpportunityCard(item) {
  return `
    <article class="industry-opportunity-card">
      <div class="industry-opportunity-card-head">
        <div>
          <span>${escapeHtml(cleanOpportunityText(item.opportunityTypeLabel || item.opportunityType || '合作机会'))}</span>
          <b>${escapeHtml(item.investedEnterprise || item.targetEnterprise || item.sourceEnterprise || '-')}</b>
        </div>
        <em>${escapeHtml(item.confidence || '-')}</em>
      </div>
      <p>${escapeHtml(buildOpportunityOneLine(item))}</p>
    </article>
  `;
}

function renderEvidenceSummary(result, stats) {
  const query = result.query || {};
  const llm = result.meta?.llm || {};
  const rows = [
    ['分析模式', industryChainModeLabel(result.mode || state.industryChainMode)],
    ['关键词', query.keyword || query.enterpriseName || '全部'],
    ['分析问题', query.question || '默认产业链分析'],
    ['DeepSeek', llm.enabled ? `${llm.provider || 'deepseek'} / ${llm.model || '-'}` : '规则摘要或未启用'],
  ];
  if (stats.emptyStages) rows.push(['空白环节', `${stats.emptyStages} 个`]);
  if (stats.highConfidenceCount) rows.push(['高置信机会', `${stats.highConfidenceCount} 条`]);
  return `
    <div class="industry-chain-evidence">
      ${rows.map(([label, value]) => `
        <div><span>${escapeHtml(label)}</span><b>${escapeHtml(value)}</b></div>
      `).join('')}
    </div>
  `;
}

function cleanOpportunityText(text) {
  const modeLabels = {
    supply_to_external: '目标公司作为客户',
    external_supply_to_portfolio: '目标公司作为供应商',
    joint_r_and_d: '联合研发',
    shared_customer: '客户协同',
    scenario_landing: '场景落地',
    factory_or_operation_support: '厂务与运营配套',
  };
  let value = String(text ?? '');
  Object.entries(modeLabels).forEach(([code, label]) => {
    const bracketed = new RegExp(`\\s*[（(]\\s*${code}\\s*[）)]`, 'g');
    const standalone = new RegExp(`\\b${code}\\b`, 'g');
    value = value.replace(bracketed, '').replace(standalone, label);
  });
  return value
    .replace(/外部企业业务画像/g, '目标公司业务画像')
    .replace(/外部企业画像/g, '目标公司画像')
    .replace(/外部企业角色/g, '目标公司角色')
    .replace(/外部企业：/g, '目标公司：')
    .replace(/外部公司合作/g, '公司合作');
}

function sanitizeIndustryChainReportText(text, result = null) {
  let value = cleanOpportunityText(text).trim();
  const scope = result?.query?.opportunityMode || result?.query?.scopeType || $('industryChainScope')?.value || 'external_company';
  const keyword = String(result?.query?.keyword || '').trim();
  if (scope === 'external_company' && keyword) {
    const targetLine = `目标公司：**${keyword}**`;
    value = value.replace(/^#\s*.+?×\s*被投企业\s*潜在合作机会分析\s*$/m, targetLine);
    if (!value.startsWith('目标公司：')) {
      value = `${targetLine}\n\n${value}`;
    }
  }
  if (scope === 'industry_direction') {
    value = value
      .replace(/\n+(?:#{1,6}\s*)?报告说明[:：]?[\s\S]*$/m, '')
      .trim();
  }
  value = value
    .replace(/\n+(?:产业方向协同|技术能力匹配|上下游协同|场景共拓|公司合作|目标公司作为客户|目标公司作为供应商|联合研发|客户协同|场景落地|厂务与运营配套)\s*\n[^\n]{2,80}(?:公司|企业|中心|院|所|集团|厂|大学|实验室)[^\n]*\n(?:high|medium|low|高|中|低)\s*\n[\s\S]*$/i, '')
    .trim();
  return value;
}

function renderIndustryChainReport(text, result = null) {
  const value = sanitizeIndustryChainReportText(text, result);
  if (!value) return '暂无分析结果';
  const tableBlocks = [];
  const textWithTableTokens = value.replace(/((?:^\|.*\|\s*$\n?){2,})/gm, (block) => {
    const token = `@@TABLE_${tableBlocks.length}@@`;
    tableBlocks.push(renderMarkdownTable(block));
    return token;
  });
  let html = escapeHtml(textWithTableTokens)
    .replace(/^###\s+(.+)$/gm, '<h4>$1</h4>')
    .replace(/^##\s+(.+)$/gm, '<h3>$1</h3>')
    .replace(/^\-\s+(.+)$/gm, '<li>$1</li>')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\n{2,}/g, '</p><p>')
    .replace(/\n/g, '<br>');
  tableBlocks.forEach((tableHtml, index) => {
    html = html.replace(`@@TABLE_${index}@@`, tableHtml);
  });
  return `<p>${html}</p>`
    .replace(/<p><h/g, '<h')
    .replace(/<\/h([34])><\/p>/g, '</h$1>')
    .replace(/<p><div class="industry-chain-table-wrap">/g, '<div class="industry-chain-table-wrap">')
    .replace(/<\/div><\/p>/g, '</div>');
}

function renderMarkdownTable(block) {
  const lines = String(block || '').trim().split('\n').filter((line) => line.trim().startsWith('|'));
  if (lines.length < 2) return escapeHtml(block);
  const parseRow = (line) => line.trim().replace(/^\|/, '').replace(/\|$/, '').split('|').map((cell) => cell.trim());
  const headers = parseRow(lines[0]);
  const bodyLines = lines.slice(2).filter((line) => !/^\|\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?$/.test(line.trim()));
  return `
    <div class="industry-chain-table-wrap report-table-wrap">
      <table class="industry-chain-table report-table">
        <thead>
          <tr>${headers.map((header) => `<th>${escapeHtml(header).replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')}</th>`).join('')}</tr>
        </thead>
        <tbody>
          ${bodyLines.map((line) => {
            const cells = parseRow(line);
            return `<tr>${headers.map((_, index) => `<td>${escapeHtml(cells[index] || '').replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')}</td>`).join('')}</tr>`;
          }).join('')}
        </tbody>
      </table>
    </div>
  `;
}

function renderIndustryChainTables(tables) {
  const list = Array.isArray(tables) ? tables : [];
  if (!list.length) return '<div class="empty">暂无数据</div>';
  return list.map((table) => {
    const columns = Array.isArray(table.columns) ? table.columns : [];
    const rows = Array.isArray(table.rows) ? table.rows : [];
    return `
      <div class="industry-chain-table-wrap">
        <div class="industry-chain-table-title">${escapeHtml(table.title || '结果明细')}</div>
        <table class="industry-chain-table">
          <thead>
            <tr>${columns.map((col) => `<th>${escapeHtml(col)}</th>`).join('')}</tr>
          </thead>
          <tbody>
            ${rows.length ? rows.map((row) => `
              <tr>${(Array.isArray(row) ? row : []).map((cell) => `<td>${escapeHtml(String(cell ?? ''))}</td>`).join('')}</tr>
            `).join('') : `<tr><td colspan="${columns.length || 1}">暂无数据</td></tr>`}
          </tbody>
        </table>
      </div>
    `;
  }).join('');
}

function industryChainReportTitle(result) {
  const mode = result?.mode || state.industryChainMode || 'overview';
  const query = result?.query || {};
  if (mode === 'graph-qa') return '图谱知识问答报告';
  const target = query.keyword || query.enterpriseName || '';
  if (target) return `${target}${industryChainModeLabel(mode)}报告`;
  return `${industryChainModeLabel(mode)}报告`;
}

function markdownTableFromRows(columns, rows) {
  const headers = Array.isArray(columns) ? columns : [];
  const bodyRows = Array.isArray(rows) ? rows : [];
  if (!headers.length) return '';
  const normalize = (value) => String(value ?? '').replace(/\r?\n/g, ' ').replace(/\|/g, '/').trim();
  const divider = headers.map(() => '---');
  const lines = [
    `| ${headers.map(normalize).join(' | ')} |`,
    `| ${divider.join(' | ')} |`,
    ...bodyRows.map((row) => `| ${headers.map((_, index) => normalize(Array.isArray(row) ? row[index] : '')).join(' | ')} |`),
  ];
  return lines.join('\n');
}

function industryChainResultToMarkdown(result) {
  if (!result) return '';
  const parts = [`# ${industryChainReportTitle(result)}`];

  const answer = sanitizeIndustryChainReportText(result.answer || '', result);
  if (answer) {
    parts.push('', answer);
  }

  const opportunities = Array.isArray(result.opportunities) ? result.opportunities : [];
  if (opportunities.length) {
    parts.push('', '## 合作机会清单', '');
    parts.push(markdownTableFromRows(
      ['企业', '合作类型', '产业链/场景', '置信度', '建议'],
      opportunities.map((item) => [
        item.investedEnterprise || item.targetEnterprise || item.sourceEnterprise || '',
        cleanOpportunityText(item.opportunityTypeLabel || item.matchedDimension || item.opportunityType || ''),
        item.subTrack || item.scenario || item.targetStage || item.sourceStage || '',
        item.confidence || '',
        buildOpportunityOneLine(item),
      ]),
    ));
  }

  const tables = Array.isArray(result.tables) ? result.tables : [];
  tables.forEach((table) => {
    parts.push('', `## ${table.title || '结果明细'}`, '');
    parts.push(markdownTableFromRows(table.columns, table.rows));
  });

  return parts.join('\n').replace(/\n{4,}/g, '\n\n\n').trim() + '\n';
}

function downloadTextFile(filename, content, mimeType) {
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function markdownToDocumentHtml(markdown, title) {
  const tableBlocks = [];
  const textWithTableTokens = String(markdown || '').replace(/((?:^\|.*\|\s*$\n?){2,})/gm, (block) => {
    const token = `@@DOC_TABLE_${tableBlocks.length}@@`;
    tableBlocks.push(renderMarkdownTable(block));
    return token;
  });
  let body = escapeHtml(textWithTableTokens)
    .replace(/^#\s+(.+)$/gm, '<h1>$1</h1>')
    .replace(/^##\s+(.+)$/gm, '<h2>$1</h2>')
    .replace(/^###\s+(.+)$/gm, '<h3>$1</h3>')
    .replace(/^-\s+(.+)$/gm, '<li>$1</li>')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\n{2,}/g, '</p><p>')
    .replace(/\n/g, '<br>');
  tableBlocks.forEach((tableHtml, index) => {
    body = body.replace(`@@DOC_TABLE_${index}@@`, tableHtml);
  });
  body = `<p>${body}</p>`
    .replace(/<p><h/g, '<h')
    .replace(/<\/h([123])><\/p>/g, '</h$1>')
    .replace(/<p><div class="industry-chain-table-wrap report-table-wrap">/g, '<div class="industry-chain-table-wrap report-table-wrap">')
    .replace(/<\/div><\/p>/g, '</div>')
    .replace(/<p><\/p>/g, '');
  return `<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>${escapeHtml(title)}</title>
  <style>
    body { font-family: "Microsoft YaHei", Arial, sans-serif; color: #1f2937; line-height: 1.7; padding: 32px; }
    h1 { font-size: 24px; margin: 0 0 18px; }
    h2, h3 { font-size: 18px; margin: 24px 0 10px; }
    h4 { font-size: 15px; margin: 18px 0 8px; }
    table { border-collapse: collapse; width: 100%; margin: 12px 0 20px; }
    th, td { border: 1px solid #d1d5db; padding: 7px 9px; vertical-align: top; }
    th { background: #f3f4f6; text-align: left; }
    .industry-chain-table-wrap { overflow: visible; }
    p { margin: 0 0 10px; }
    li { margin: 4px 0 4px 18px; }
  </style>
</head>
<body>${body}</body>
</html>`;
}

function exportIndustryChainPdf(title, html) {
  const win = window.open('', '_blank', 'width=960,height=720');
  if (!win) {
    showMessage('浏览器阻止了导出窗口，请允许弹窗后重试。', 'error');
    return;
  }
  win.document.write(html);
  win.document.close();
  win.focus();
  setTimeout(() => win.print(), 300);
}

function exportIndustryChainReport() {
  const mode = currentIndustryChainMode();
  const result = isIndustryChainResultCurrent(state.industryChainResult, mode) ? state.industryChainResult : null;
  if (!result) {
    showMessage('暂无可导出的产业链报告，请先完成一次分析。', 'error');
    return;
  }
  const format = $('industryChainExportFormat')?.value || 'pdf';
  const title = industryChainReportTitle(result);
  const basename = safeFileName(`${title}-${formatDateKey(new Date())}`);
  const markdown = industryChainResultToMarkdown(result);
  if (format === 'md') {
    downloadTextFile(`${basename}.md`, markdown, 'text/markdown;charset=utf-8');
    showMessage('Markdown 报告已导出。', 'success');
    return;
  }
  const html = markdownToDocumentHtml(markdown, title);
  if (format === 'doc') {
    downloadTextFile(`${basename}.doc`, html, 'application/msword;charset=utf-8');
    showMessage('Word DOC 报告已导出。', 'success');
    return;
  }
  exportIndustryChainPdf(title, html);
  showMessage('已打开 PDF 打印窗口，可选择保存为 PDF。', 'success');
}

function renderIndustryChainRelationTable(tables) {
  const table = Array.isArray(tables) ? tables[0] : null;
  if (!table) return '';
  const columns = Array.isArray(table.columns) ? table.columns : [];
  const rows = Array.isArray(table.rows) ? table.rows : [];
  if (!rows.length) return '<div class="empty">暂无上下游关系</div>';
  const pageSize = 10;
  const visibleCount = Math.max(pageSize, Math.min(Number(state.industryChainRelationVisibleCount) || pageSize, rows.length));
  state.industryChainRelationVisibleCount = visibleCount;
  const visibleRows = rows.slice(0, visibleCount);
  return `
    <div class="industry-chain-relation-window">
      <div class="industry-chain-relation-head">
        <b>${escapeHtml(table.title || '上下游关联企业明细')}</b>
        <span>${escapeHtml(visibleRows.length)} / ${escapeHtml(rows.length)}</span>
      </div>
      <div class="industry-chain-table-wrap industry-chain-relation-scroll">
        <table class="industry-chain-table">
          <thead>
            <tr>${columns.map((col) => `<th>${escapeHtml(col)}</th>`).join('')}</tr>
          </thead>
          <tbody>
            ${visibleRows.map((row) => `
              <tr>${(Array.isArray(row) ? row : []).map((cell) => `<td>${escapeHtml(String(cell ?? ''))}</td>`).join('')}</tr>
            `).join('')}
          </tbody>
        </table>
        ${visibleRows.length < rows.length ? '<div class="industry-chain-relation-more">向下滚动加载更多</div>' : ''}
      </div>
    </div>
  `;
}

function renderIndustryChain(options = {}) {
  syncIndustryChainControls();
  const status = state.industryChainStatus || {};
  const mode = currentIndustryChainMode();
  const result = isIndustryChainResultCurrent(state.industryChainResult, mode) ? state.industryChainResult : null;
  const isCompanyUpdownMode = mode === 'company-updown';
  const isOpportunityMode = mode === 'opportunities';
  const isGraphQaMode = mode === 'graph-qa';
  const runStatus = state.industryChainRunStatus;
  const statusEl = $('industryChainStatusText');
  if (statusEl) {
    if (runStatus?.running) {
      const elapsedSeconds = Math.max(0, Math.floor((Date.now() - Number(runStatus.startedAt || Date.now())) / 1000));
      statusEl.className = 'message info industry-chain-status';
      statusEl.textContent = `${runStatus.message || '产业链分析运行中...'} 已等待 ${elapsedSeconds} 秒，请勿重复提交。`;
    } else if (runStatus?.error) {
      statusEl.className = 'message error industry-chain-status';
      statusEl.textContent = runStatus.message || '产业链分析失败';
    } else if (status?.ok === false) {
      statusEl.className = 'message error industry-chain-status';
      statusEl.textContent = status?.message || '产业链分析模块连接失败';
    } else {
      statusEl.className = 'message success industry-chain-status hidden';
      statusEl.textContent = '';
    }
  }

  const rowCount = result?.meta?.rowCount ?? 0;
  setText('industryChainCount', String(rowCount || 0));
  const exportControls = $('industryChainExportControls');
  const exportBtn = $('industryChainExportBtn');
  if (exportControls) exportControls.classList.toggle('hidden', !isOpportunityMode);
  if (exportBtn) exportBtn.disabled = !isOpportunityMode || !result;
  const dashboardGrid = $('industryChainDashboard')?.closest('.grid');
  if (dashboardGrid) dashboardGrid.classList.toggle('hidden', isCompanyUpdownMode || isOpportunityMode || isGraphQaMode);
  const graphPanel = document.querySelector('.industry-chain-graph-panel');
  if (graphPanel) {
    graphPanel.classList.toggle('hidden', isOpportunityMode || isGraphQaMode);
    const graphTitle = graphPanel.querySelector('.panel-header h3');
    const trackPicker = graphPanel.querySelector('.industry-chain-track-picker');
    if (graphTitle) graphTitle.textContent = isCompanyUpdownMode ? '关系图谱' : '产业链树状图';
    if (trackPicker) trackPicker.classList.toggle('hidden', mode !== 'overview');
  }
  const networkPanel = document.querySelector('.industry-chain-network-panel');
  if (networkPanel) networkPanel.classList.toggle('hidden', isCompanyUpdownMode || isOpportunityMode || isGraphQaMode);
  const answerPanel = $('industryChainAnswerPanel');
  if (answerPanel) {
    answerPanel.style.display = (mode === 'overview' && !runStatus?.running) || isOpportunityMode ? 'none' : '';
    const answerTitle = answerPanel.querySelector('.panel-header h3');
    if (answerTitle) answerTitle.textContent = isGraphQaMode ? '图谱回答' : '上下游关系';
  }
  const opportunitySection = $('industryChainOpportunitySection');
  if (opportunitySection) opportunitySection.classList.toggle('hidden', !isOpportunityMode);
  const opportunityTitle = $('industryChainOpportunityTitle');
  if (opportunityTitle) {
    const scope = result?.query?.opportunityMode || result?.query?.scopeType || currentIndustryChainScope();
    opportunityTitle.textContent = industryChainOpportunityScopeLabel(scope);
  }
  setText('industryChainOpportunityCount', String(result?.opportunities?.length || 0));
  const opportunityEl = $('industryChainOpportunityResults');
  if (opportunityEl) {
    const loadingHtml = isOpportunityMode && runStatus?.running
      ? `<div class="industry-chain-loading-state">
          <b>正在探索合作机会</b>
          <span>${escapeHtml(runStatus.message || '正在召回候选企业并生成报告...')}</span>
          <small>页面仍在等待后端响应，完成后会自动刷新结果。</small>
        </div>`
      : '';
    const html = loadingHtml || (isOpportunityMode && result ? renderOpportunityCards(result) : '');
    opportunityEl.className = html ? 'industry-chain-opportunity-results' : 'industry-chain-opportunity-results empty';
    opportunityEl.innerHTML = html || '暂无合作机会';
  }
  if (isGraphQaMode) {
    resetIndustryChainNetwork();
    state.industryChainNetworkRequested = false;
  }
  const questionAnswerEl = $('industryChainQuestionAnswer');
  if (!result && questionAnswerEl) {
    questionAnswerEl.className = 'industry-chain-question-answer hidden';
    questionAnswerEl.innerHTML = '';
  }
  const dashboardEl = $('industryChainDashboard');
  if (dashboardEl) {
    dashboardEl.className = result ? 'industry-chain-dashboard' : 'industry-chain-dashboard empty';
    dashboardEl.innerHTML = renderIndustryChainDashboard(result);
  }
  const answerEl = $('industryChainAnswer');
  if (answerEl) {
    const fallbackAnswer = result && !result.answer ? '当前图谱已返回结构化结果，但暂未生成文字报告。请点击“分析”重新生成。' : '';
    const answer = result?.answer || fallbackAnswer;
    answerEl.className = answer ? 'industry-chain-answer' : 'industry-chain-answer empty';
    answerEl.innerHTML = answer ? renderIndustryChainReport(answer, result) : '暂无分析结果';
  }
  const relationEl = $('industryChainRelationSummary');
  if (relationEl) {
    const graphQaLoadingHtml = isGraphQaMode && runStatus?.running
      ? `<div class="industry-chain-loading-state">
          <b>正在检索图谱</b>
          <span>${escapeHtml(runStatus.message || '正在检索 Neo4j 图谱并生成回答...')}</span>
          <small>页面仍在等待后端响应，完成后会自动刷新结果。</small>
        </div>`
      : '';
    const relationHtml = graphQaLoadingHtml || (
      isGraphQaMode
        ? (result ? `<div class="industry-chain-report">${renderIndustryChainReport(result.answer || '', result)}</div>${renderIndustryChainTables(result.tables)}` : '')
        : (result?.tables?.length ? renderIndustryChainRelationTable(result.tables) : '')
    );
    relationEl.className = relationHtml ? 'industry-chain-answer' : 'industry-chain-answer empty';
    relationEl.innerHTML = relationHtml || (isGraphQaMode ? '暂无图谱问答结果' : '暂无上下游关系');
  }
  const graphEl = $('industryChainGraph');
  if (graphEl) {
    if (isOpportunityMode || isGraphQaMode) {
      resetIndustryChainNetwork();
      state.industryChainNetworkRequested = false;
      graphEl.className = 'industry-chain-graph empty compact-empty';
      graphEl.innerHTML = isGraphQaMode ? '图谱知识问答不显示图谱' : '合作机会探索不显示图谱';
      renderIndustryNetworkPlaceholder(isGraphQaMode ? '图谱知识问答不显示产业链图谱' : '合作机会探索不显示产业链图谱');
    } else if (isCompanyUpdownMode) {
      resetIndustryChainNetwork();
      state.industryChainNetworkRequested = false;
      updateIndustryChainTrackSelect(null);
      graphEl.className = result?.graph ? 'industry-chain-graph' : 'industry-chain-graph empty compact-empty';
      graphEl.innerHTML = result?.graph ? renderIndustryChainGraph(result.graph) : '暂无上下游分析结果';
      renderIndustryNetworkPlaceholder('产业链上下游模式不显示全景网络图');
    } else {
      graphEl.className = result?.graph ? 'industry-chain-graph' : 'industry-chain-graph empty';
      if (result?.graph) updateIndustryChainTrackSelect(result.graph);
      graphEl.innerHTML = result?.graph ? renderIndustryChainGraph(result.graph) : '暂无图谱';
      if (result?.graph) {
        const requiresNetworkConfirmation = state.industryChainSelectedTrackId === INDUSTRY_CHAIN_ALL_TRACKS;
        if ((!requiresNetworkConfirmation || state.industryChainNetworkRequested) && !options.skipNetwork) {
          const scheduleNetwork = window.requestIdleCallback || ((callback) => setTimeout(callback, 80));
          scheduleNetwork(() => renderIndustryChainNetwork(result.graph));
        } else if (requiresNetworkConfirmation && !state.industryChainNetworkRequested) {
          resetIndustryChainNetwork();
          renderIndustryNetworkPlaceholder('产业链全貌节点较多，点击后渲染网络图');
        }
      } else {
        resetIndustryChainNetwork();
        state.industryChainNetworkRequested = false;
        updateIndustryChainTrackSelect(null);
        renderIndustryNetworkPlaceholder('暂无图谱');
      }
    }
  }
  const tablesEl = $('industryChainTables');
  if (tablesEl) {
    tablesEl.className = 'industry-chain-tables hidden';
    tablesEl.innerHTML = '';
  }
  const suggestionsEl = $('industryChainSuggestions');
  if (suggestionsEl) {
    suggestionsEl.innerHTML = '';
  }
}

function highlightQuery(text, query) {
  if (!text || !query) return escapeHtml(text);
  const escaped = escapeHtml(text);
  const q = escapeHtml(query);
  if (!q) return escaped;
  // Escape regex special chars and build case-insensitive pattern
  const pattern = q.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  if (!new RegExp(pattern, 'iu').test(text)) return escaped;
  return escaped.replace(new RegExp('(' + pattern + ')', 'giu'), '<mark class="search-highlight">$1</mark>');
}

function companyWebsiteUrl(item) {
  const raw = item?.raw || {};
  const direct = String(
    raw['官网URL'] || raw['官网'] || raw['网址'] || raw['网站'] || raw['URL'] || item?.url || '',
  ).trim();
  if (direct) return direct.startsWith('http') ? direct : `https://${direct}`;
  const name = String(item?.title || raw['公司名称'] || '').trim();
  return name ? `https://www.baidu.com/s?wd=${encodeURIComponent(name + ' 官网')}` : '#';
}

function companyField(raw, key, fallback = '—') {
  const value = raw && typeof raw === 'object' ? raw[key] : '';
  return escapeHtml(value || fallback);
}

function highlightedCompanyField(raw, key, fallback = '—') {
  const value = raw && typeof raw === 'object' ? raw[key] : '';
  return highlightQuery((value || fallback).toString(), state.companyQueryLastQuery);
}

function initCompanySummaryPdfViewers(rootEl) {
  const pdfjs = window.pdfjsLib;
  if (!rootEl || !pdfjs) return;
  if (!pdfjs.GlobalWorkerOptions.workerSrc) {
    pdfjs.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';
  }

  rootEl.querySelectorAll('[data-pdf-src]').forEach(async (viewerEl) => {
    const src = viewerEl.getAttribute('data-pdf-src');
    const canvas = viewerEl.querySelector('.company-summary-pdf-canvas');
    const slider = viewerEl.querySelector('[data-pdf-slider]');
    const indexEl = viewerEl.querySelector('[data-pdf-index]');
    const openLink = viewerEl.querySelector('[data-pdf-open]');
    const prevBtn = viewerEl.querySelector('[data-pdf-prev]');
    const nextBtn = viewerEl.querySelector('[data-pdf-next]');
    const rotateLeftBtn = viewerEl.querySelector('[data-pdf-rotate-left]');
    const rotateRightBtn = viewerEl.querySelector('[data-pdf-rotate-right]');
    const rotateLabel = viewerEl.querySelector('[data-pdf-rotate-label]');
    const loadingEl = viewerEl.querySelector('[data-pdf-loading]');
    if (!src || !canvas) return;

    try {
      if (openLink) openLink.href = src;
      const pdf = await pdfjs.getDocument(src).promise;
      const total = pdf.numPages || 1;
      let current = 1;
      let manualRotation = 0;
      let renderVersion = 0;
      let currentRenderTask = null;
      let wheelLockUntil = 0;
      if (slider) slider.max = String(Math.max(total - 1, 0));
      const ctx = canvas.getContext('2d');

      const renderPage = async (pageNum, resetRotation = false) => {
        current = Math.max(1, Math.min(total, Number(pageNum) || 1));
        if (resetRotation) manualRotation = 0;
        const myVersion = ++renderVersion;

        if (currentRenderTask && typeof currentRenderTask.cancel === 'function') {
          try { currentRenderTask.cancel(); } catch {}
        }
        currentRenderTask = null;

        const page = await pdf.getPage(current);
        if (myVersion !== renderVersion) return;

        const baseRotation = ((Number(page.rotate) || 0) % 360 + 360) % 360;
        const finalRotation = (baseRotation + manualRotation + 360) % 360;
        const baseViewport = page.getViewport({ scale: 1, rotation: finalRotation });
        const containerWidth = Math.max(viewerEl.clientWidth - 24, 320);
        const maxRenderHeight = Math.max(Math.min(window.innerHeight * 0.68, 980), 420);
        const widthScale = containerWidth / Math.max(baseViewport.width, 1);
        const heightScale = maxRenderHeight / Math.max(baseViewport.height, 1);
        const scale = Math.min(widthScale, heightScale);
        const viewport = page.getViewport({ scale, rotation: finalRotation });

        canvas.width = Math.floor(viewport.width);
        canvas.height = Math.floor(viewport.height);

        const task = page.render({ canvasContext: ctx, viewport });
        currentRenderTask = task;
        try {
          await task.promise;
        } catch (error) {
          if (error?.name === 'RenderingCancelledException' || /cancel/i.test(String(error?.message || ''))) {
            return;
          }
          throw error;
        }
        if (myVersion !== renderVersion || task !== currentRenderTask) return;

        if (slider) slider.value = String(current - 1);
        if (indexEl) indexEl.textContent = `${current} / ${total}`;
        if (rotateLabel) rotateLabel.textContent = `${finalRotation}°`;
        if (loadingEl) loadingEl.style.display = 'none';
      };

      viewerEl.__pdfRenderCurrent = () => renderPage(current);
      viewerEl.__pdfRenderPage = (pageNum) => renderPage(pageNum);

      const isVisible = () => viewerEl.offsetParent !== null && getComputedStyle(viewerEl).display !== 'none';

      if (slider) slider.addEventListener('input', () => renderPage(Number(slider.value || 0) + 1, true));
      if (prevBtn) prevBtn.addEventListener('click', () => renderPage(current - 1, true));
      if (nextBtn) nextBtn.addEventListener('click', () => renderPage(current + 1, true));
      if (rotateLeftBtn) rotateLeftBtn.addEventListener('click', () => { manualRotation = (manualRotation - 90 + 360) % 360; renderPage(current); });
      if (rotateRightBtn) rotateRightBtn.addEventListener('click', () => { manualRotation = (manualRotation + 90) % 360; renderPage(current); });
      viewerEl.addEventListener('wheel', (event) => {
        event.preventDefault();
        const now = Date.now();
        if (now < wheelLockUntil) return;
        wheelLockUntil = now + 180;
        if (event.deltaY > 0) renderPage(current + 1, true);
        else if (event.deltaY < 0) renderPage(current - 1, true);
      }, { passive: false });
      window.addEventListener('resize', () => {
        if (isVisible()) renderPage(current);
      });

      if (isVisible()) {
        requestAnimationFrame(() => renderPage(1));
      }
    } catch (error) {
      viewerEl.innerHTML = `<div class="company-summary-gallery-empty">PDF 加载失败：${escapeHtml(String(error?.message || error || 'unknown error'))}</div>`;
    }
  });
}

function renderCompanySummaryGallery(item) {
  const sectionEl = $('companySummarySection');
  const galleryEl = $('companySummaryGallery');
  const metaEl = $('companySummaryGalleryMeta');
  const countEl = $('companySummaryGalleryCount');
  if (!galleryEl) return;

  const images = Array.isArray(item?.summaryImages)
    ? item.summaryImages.filter((src) => typeof src === 'string' && src.trim())
    : [];
  const isPdf = (src) => /\.pdf(?:$|\?)/i.test(String(src || ''));
  const companyName = item?.title || item?.raw?.['公司名称'] || '';

  if (!companyName) {
    if (sectionEl) sectionEl.style.display = 'none';
    if (countEl) countEl.textContent = '0';
    if (metaEl) metaEl.textContent = '选中企业后在这里查看配图';
    galleryEl.className = 'company-summary-gallery empty';
    galleryEl.innerHTML = '暂无图片';
    return;
  }

  if (sectionEl) sectionEl.style.display = '';
  if (countEl) countEl.textContent = String(images.length || 0);
  if (metaEl) {
    metaEl.textContent = `${companyName} 的企业简介`;
  }

  galleryEl.className = 'company-summary-gallery';
  galleryEl.innerHTML = `
    <div class="company-summary-profile-wrap">
      ${renderCompanyProfileCard(item)}
    </div>
    ${images.length ? `
      <div class="company-summary-pager" id="companySummaryPager">
        <div class="company-summary-pager-track" id="companySummaryPagerTrack">
          ${images.map((src, idx) => `
            ${isPdf(src)
              ? `
                <div class="company-summary-pdf-viewer" data-pdf-src="${escapeHtml(src)}">
                  <div class="company-summary-pdf-canvas-wrap">
                    <canvas class="company-summary-pdf-canvas"></canvas>
                  </div>
                  <div class="company-summary-pdf-loading" data-pdf-loading>加载 PDF…</div>
                  <div class="company-summary-pdf-controls">
                    <button type="button" class="secondary small-btn" data-pdf-prev>↑</button>
                    <input class="company-summary-pdf-slider" data-pdf-slider type="range" min="0" max="0" step="1" value="0" />
                    <button type="button" class="secondary small-btn" data-pdf-next>↓</button>
                    <span class="company-summary-pdf-index" data-pdf-index>1 / 1</span>
                    <button type="button" class="secondary small-btn" data-pdf-rotate-left>↺</button>
                    <button type="button" class="secondary small-btn" data-pdf-rotate-right>↻</button>
                    <span class="company-summary-pdf-rotate-label" data-pdf-rotate-label>0°</span>
                    <a class="secondary small-btn company-summary-pdf-open" data-pdf-open target="_blank" rel="noreferrer noopener">打开 PDF</a>
                  </div>
                </div>
              `
              : `<div class="company-summary-image-panel"><a class="company-summary-image-link" href="${escapeHtml(src)}" target="_blank" rel="noreferrer noopener"><img class="company-summary-image" src="${escapeHtml(src)}" alt="${escapeHtml(companyName)} 图片 ${idx + 1}" loading="lazy" /></a></div>`
            }
          `).join('')}
        </div>
        ${images.length > 1 ? `
          <div class="company-summary-pager-controls">
            <button type="button" class="secondary small-btn" id="companySummaryPagerPrev">上一份</button>
            <span class="company-summary-pager-index" id="companySummaryPagerIndex">资料 1 / ${images.length}</span>
            <button type="button" class="secondary small-btn" id="companySummaryPagerNext">下一份</button>
          </div>
        ` : ''}
      </div>
    ` : ''}
  `;

  const pagerEl = $('companySummaryPager');
  const trackEl = $('companySummaryPagerTrack');
  const prevBtn = $('companySummaryPagerPrev');
  const nextBtn = $('companySummaryPagerNext');
  const indexEl = $('companySummaryPagerIndex');

  if (trackEl && images.length > 0) {
    const slides = Array.from(trackEl.children);
    let currentSlide = 0;
    const goSlide = (n) => {
      const idx = Math.max(0, Math.min(images.length - 1, Number(n) || 0));
      slides.forEach((slide, i) => slide.classList.toggle('is-active', i === idx));
      currentSlide = idx;
      if (indexEl) indexEl.textContent = `资料 ${idx + 1} / ${images.length}`;
      const activeSlide = slides[idx];
      if (activeSlide && typeof activeSlide.__pdfRenderCurrent === 'function') {
        requestAnimationFrame(() => requestAnimationFrame(() => activeSlide.__pdfRenderCurrent()));
      }
    };
    goSlide(0);
    if (prevBtn) prevBtn.addEventListener('click', () => goSlide((currentSlide - 1 + images.length) % images.length));
    if (nextBtn) nextBtn.addEventListener('click', () => goSlide((currentSlide + 1) % images.length));
    if (pagerEl) {
      pagerEl.addEventListener('wheel', (event) => {
        const activeSlide = slides[currentSlide];
        if (activeSlide && activeSlide.matches('.company-summary-pdf-viewer')) return;
        event.preventDefault();
        if (event.deltaY > 0) goSlide((currentSlide + 1) % images.length);
        else if (event.deltaY < 0) goSlide((currentSlide - 1 + images.length) % images.length);
      }, { passive: false });
    }
  }

  initCompanySummaryPdfViewers(galleryEl);
}

function renderCompanyProfileCard(item) {
  const raw = item?.raw || {};
  const title = escapeHtml(item?.title || raw['公司名称'] || '未命名企业');
  const titleHighlighted = highlightQuery(item?.title || raw['公司名称'] || '未命名企业', state.companyQueryLastQuery);
  const websiteUrl = companyWebsiteUrl(item);
  const titleLink = websiteUrl && websiteUrl !== '#'
    ? `<a class="company-name-link" href="${escapeHtml(websiteUrl)}" target="_blank" rel="noreferrer noopener">官网首页 ↗</a>`
    : `<span class="company-name-link disabled">无官网信息</span>`;
  const tech = highlightedCompanyField(raw, '核心技术');
  const product = highlightedCompanyField(raw, '产品');
  const maturity = highlightedCompanyField(raw, '技术成熟度');
  const industry = highlightedCompanyField(raw, '产品应用行业');
  const customers = highlightedCompanyField(raw, '客户');
  const suppliers = highlightedCompanyField(raw, '供应商');
  const scene = highlightedCompanyField(raw, '应用场景');
  const futureScene = highlightedCompanyField(raw, '可能应用场景');
  const model = highlightedCompanyField(raw, '商务模式');
  const delivery = highlightedCompanyField(raw, '交付能力');
  const certs = highlightedCompanyField(raw, '认证/资质/知识产权');
  const team = highlightedCompanyField(raw, '创始团队与短板');
  const resources = highlightedCompanyField(raw, '当前最需要的资源类型');
  const revenue = highlightedCompanyField(raw, '近三年营收及利润');
  const competition = highlightedCompanyField(raw, '竞对及技术差异');
  const matchLevel = highlightedCompanyField(raw, '匹配程度');
  const tags = Array.isArray(item?.matchedTargets)
    ? item.matchedTargets.filter((tag) => tag && tag !== '企业查询').slice(0, 4)
    : [];

  return `
    <article class="company-profile-card">
      <div class="company-profile-head">
        <div>
          <h4>${titleLink}</h4>
        </div>
        ${tags.length ? `<div class="tags">${tags.map((tag) => `<span class="tag">${escapeHtml(tag)}</span>`).join('')}</div>` : ''}
      </div>
      <div class="company-profile-grid">
        <div class="profile-field profile-span-2"><span class="profile-label">核心技术</span><div class="profile-value">${tech}</div></div>
        <div class="profile-field profile-span-2"><span class="profile-label">产品</span><div class="profile-value">${product}</div></div>
        <div class="profile-field"><span class="profile-label">技术成熟度</span><div class="profile-value">${maturity}</div></div>
        <div class="profile-field"><span class="profile-label">产品应用行业</span><div class="profile-value">${industry}</div></div>
        <div class="profile-field profile-span-2"><span class="profile-label">客户</span><div class="profile-value">${customers}</div></div>
        <div class="profile-field"><span class="profile-label">供应商</span><div class="profile-value">${suppliers}</div></div>
        <div class="profile-field"><span class="profile-label">匹配程度</span><div class="profile-value">${matchLevel}</div></div>
        <div class="profile-field profile-span-2"><span class="profile-label">应用场景</span><div class="profile-value">${scene}</div></div>
        <div class="profile-field profile-span-2"><span class="profile-label">可能应用场景</span><div class="profile-value">${futureScene}</div></div>
        <div class="profile-field"><span class="profile-label">商务模式</span><div class="profile-value">${model}</div></div>
        <div class="profile-field"><span class="profile-label">交付能力</span><div class="profile-value">${delivery}</div></div>
        <div class="profile-field profile-span-2"><span class="profile-label">认证 / 资质 / 知识产权</span><div class="profile-value">${certs}</div></div>
        <div class="profile-field profile-span-2"><span class="profile-label">创始团队与短板</span><div class="profile-value">${team}</div></div>
        <div class="profile-field"><span class="profile-label">当前最需要的资源类型</span><div class="profile-value">${resources}</div></div>
        <div class="profile-field"><span class="profile-label">近三年营收及利润</span><div class="profile-value">${revenue}</div></div>
        <div class="profile-field profile-span-2"><span class="profile-label">竞对及技术差异</span><div class="profile-value">${competition}</div></div>
      </div>
    </article>
  `;
}

let _companyQueryDetailViewId = null;

function renderCompanyQueryResults(items) {
  if (!Array.isArray(items) || !items.length) return '';
  const rowsHtml = items.map((item, idx) => {
    const raw = item?.raw || {};
    const title = escapeHtml(item?.title || raw['公司名称'] || '未命名企业');
    const titleHtml = highlightQuery(item?.title || raw['公司名称'] || '未命名企业', state.companyQueryLastQuery);
    const industry = companyField(raw, '产品应用行业');
    const tech = companyField(raw, '核心技术');
    const isDetail = _companyQueryDetailViewId === idx;
    const url = companyWebsiteUrl(item);
    const rowTitle = url && url !== '#' ? title + ' · ' + url : title;
    return `
      <button class="company-browse-row${isDetail ? ' is-expanded' : ''}" type="button" data-query-row="${idx}">
        <div class="company-browse-row-title" title="${rowTitle}">${titleHtml}</div>
        <div class="company-browse-row-meta" title="${escapeHtml(industry)}">${industry}</div>
        <div class="company-browse-row-tech" title="${escapeHtml(tech)}">${tech}</div>
        <div class="company-browse-row-toggle">${isDetail ? '已选中' : '查看简介'}</div>
      </button>
    `;
  }).join('');
  return `<div class="company-browse-list">${rowsHtml}</div>`;
}

/* ── 企业浏览（可滚动列表 + 展开收缩） ── */

const COMPANY_BROWSE_INITIAL_ROWS = 10;
let _companyBrowseExpanded = false; // 展开/收缩状态
let _companyBrowseDetailViewId = null; // 当前展开详情的行索引

function renderCompanyBrowseRail(items) {
  if (!Array.isArray(items) || !items.length) return '';
  // 默认折叠：不显示行，只显示展开按钮
  if (!_companyBrowseExpanded) {
    return `<div class="company-browse-actions"><button class="company-browse-expand-btn" type="button" id="companyBrowseExpandBtn">展开全部（共 ${items.length} 家）▾</button></div>`;
  }
  const visibleRows = items;
  const rowsHtml = visibleRows.map((item, idx) => {
    const raw = item?.raw || {};
    const title = escapeHtml(item?.title || raw['公司名称'] || '未命名企业');
    const industry = companyField(raw, '产品应用行业');
    const tech = companyField(raw, '核心技术');
    const isDetail = _companyBrowseDetailViewId === idx;
    const url = companyWebsiteUrl(item);
    const rowTitle = url && url !== '#' ? title + ' · ' + url : title;
    return `
      <button class="company-browse-row${isDetail ? ' is-expanded' : ''}" type="button" data-browse-row="${idx}">
        <div class="company-browse-row-title" title="${rowTitle}">${title}</div>
        <div class="company-browse-row-meta" title="${escapeHtml(industry)}">${industry}</div>
        <div class="company-browse-row-tech" title="${escapeHtml(tech)}">${tech}</div>
        <div class="company-browse-row-toggle">${isDetail ? '已选中' : '查看简介'}</div>
      </button>
    `;
  }).join('');

  const expandBtnText = '收起△';
  const expandHtml = `<button class="company-browse-expand-btn" type="button" id="companyBrowseExpandBtn" data-collapse="true">${expandBtnText}</button>`;

  return `
    <div class="company-browse-list">${rowsHtml}</div>
    <div class="company-browse-actions">${expandHtml}</div>
  `;
}

function renderCompanyBrowse() {
  const browseItems = Array.isArray(state.companyBrowseItems) ? state.companyBrowseItems : [];
  const el = $('companyBrowseRail');
  setText('companyBrowseCount', String(browseItems.length || 0));
  if (!el) return;

  const listBefore = el.querySelector('.company-browse-list');
  const prevScrollTop = listBefore ? listBefore.scrollTop : 0;
  const prevExpanded = _companyBrowseDetailViewId;

  if (!browseItems.length) {
    el.innerHTML = '<div class="company-browse-list empty">暂无数据</div>';
    return;
  }
  el.innerHTML = renderCompanyBrowseRail(browseItems);

  const listAfter = el.querySelector('.company-browse-list');
  if (listAfter) {
    listAfter.scrollTop = prevScrollTop;
    if (prevExpanded !== null && prevExpanded !== undefined) {
      const activeRow = listAfter.querySelector(`[data-browse-row="${prevExpanded}"]`);
      if (activeRow) {
        const rowTop = activeRow.offsetTop;
        const rowBottom = rowTop + activeRow.offsetHeight;
        const viewTop = listAfter.scrollTop;
        const viewBottom = viewTop + listAfter.clientHeight;
        if (rowTop < viewTop || rowBottom > viewBottom) {
          activeRow.scrollIntoView({ block: 'nearest' });
        }
      }
    }
  }

  // 行点击
  el.querySelectorAll('[data-browse-row]').forEach((btn) => {
    btn.addEventListener('click', () => {
      const idx = parseInt(btn.getAttribute('data-browse-row'), 10);
      _companyQueryDetailViewId = null;
      _companyBrowseDetailViewId = (_companyBrowseDetailViewId === idx) ? null : idx;
      renderCompanyQuery();
    });
  });
  // 展开/收起
  const expandBtn = $('companyBrowseExpandBtn');
  if (expandBtn) {
    expandBtn.addEventListener('click', () => {
      _companyBrowseExpanded = !_companyBrowseExpanded;
      if (!_companyBrowseExpanded) _companyBrowseDetailViewId = null;
      renderCompanyQuery();
    });
  }
}

function currentCompanySummaryItem() {
  const queryItems = Array.isArray(state.companyQueryResults) ? state.companyQueryResults : [];
  const browseItems = Array.isArray(state.companyBrowseItems) ? state.companyBrowseItems : [];

  if (_companyQueryDetailViewId !== null && _companyQueryDetailViewId !== undefined && queryItems[_companyQueryDetailViewId]) {
    return queryItems[_companyQueryDetailViewId];
  }
  if (_companyBrowseDetailViewId !== null && _companyBrowseDetailViewId !== undefined && browseItems[_companyBrowseDetailViewId]) {
    return browseItems[_companyBrowseDetailViewId];
  }
  return null;
}

function renderCompanyQuery() {
  const meta = state.companyQueryStatus || {};
  const results = Array.isArray(state.companyQueryResults) ? state.companyQueryResults : [];
  setText('companyQueryCount', String(results.length || 0));
  const sourceSelect = $('companyQuerySource');
  if (sourceSelect) sourceSelect.value = state.companyQuerySource || 'xlsx';
  renderCompanyQueryHistory();
  renderCompanyBrowse();

  const qList = $('companyQueryList');
  const prevScroll = qList ? qList.querySelector('.company-browse-list') : null;
  const prevTop = prevScroll ? prevScroll.scrollTop : 0;
  const prevExpanded = _companyQueryDetailViewId;

  renderNewsList('companyQueryList', 'companyQueryCount', results, renderCompanyQueryResults);

  const curList = qList ? qList.querySelector('.company-browse-list') : null;
  if (curList) {
    curList.scrollTop = prevTop;
    if (prevExpanded !== null && prevExpanded !== undefined) {
      const activeRow = curList.querySelector('[data-query-row="' + prevExpanded + '"]');
      if (activeRow) activeRow.scrollIntoView({ block: 'nearest' });
    }
  }

  const queryListEl = $('companyQueryList');
  if (queryListEl) {
    queryListEl.querySelectorAll('[data-query-row]').forEach((btn) => {
      btn.addEventListener('click', () => {
        const idx = parseInt(btn.getAttribute('data-query-row'), 10);
        _companyBrowseDetailViewId = null;
        _companyQueryDetailViewId = (_companyQueryDetailViewId === idx) ? null : idx;
        renderCompanyQuery();
      });
    });
  }

  renderCompanySummaryGallery(currentCompanySummaryItem());
}

function renderCompetitiveStatusMeta(runtime = {}) {
  const entries = [
    ['搜索入口', runtime.searchProvider || '-'],
    ['SearXNG', runtime.searxngBaseUrl || '-'],
    ['SSL校验', runtime.searxngVerifySsl ? '开启' : '关闭'],
    ['主LLM', runtime.deepseekModel || runtime.qwenModel || '-'],
    ['Python', runtime.pythonExecutable || '-'],
    ['已屏蔽搜索API', Array.isArray(runtime.searchFallbacksBlocked) ? runtime.searchFallbacksBlocked.join(' / ') : '-'],
  ];
  return entries.map(([label, value]) => `
    <div class="competitive-kv-card">
      <div class="competitive-kv-label">${escapeHtml(label)}</div>
      <div class="competitive-kv-value">${escapeHtml(String(value || '-'))}</div>
    </div>
  `).join('');
}

function renderCompetitiveReportRail(items) {
  if (!Array.isArray(items) || !items.length) return '';
  return items.map((item) => `
    <button class="competitive-report-card" type="button" data-report-id="${escapeHtml(item.id || '')}">
      <div class="competitive-report-title">${escapeHtml(item.title || item.id || '未命名报告')}</div>
      <div class="competitive-report-meta-line">${escapeHtml(item.period || '-')}</div>
      <div class="competitive-report-meta-line">${escapeHtml(item.generatedAt || '')}</div>
    </button>
  `).join('');
}

function renderCompetitiveSummaryCards(items) {
  if (!Array.isArray(items) || !items.length) return '';
  return items.map((item) => `
    <article class="competitive-summary-card">
      <div class="competitive-summary-title">${escapeHtml(item.title || item.key || '摘要')}</div>
      <div class="competitive-summary-body">${escapeHtml(String(item.summary || '')).replaceAll('\n', '<br/>')}</div>
    </article>
  `).join('');
}

function renderCompetitiveSections(sections) {
  if (!Array.isArray(sections) || !sections.length) return '';
  return sections.map((section) => `
    <section class="competitive-section-card">
      <h4>${escapeHtml(section.title || '章节')}</h4>
      <div class="competitive-section-body">${escapeHtml(String(section.content || '')).replaceAll('\n', '<br/>')}</div>
    </section>
  `).join('');
}

function renderCompetitiveReportMeta(report) {
  if (!report) return '暂无数据';
  const entries = [
    ['报告标题', report.title || '-'],
    ['周期', report.period || '-'],
    ['运行目录', report.folder || '-'],
    ['生成时间', report.generatedAt || '-'],
    ['Markdown文件', report.reportFile || '-'],
    ['原始数据', report.rawDataFile || '-'],
  ];
  return entries.map(([label, value]) => `
    <div class="competitive-meta-row">
      <span class="competitive-meta-label">${escapeHtml(label)}</span>
      <span class="competitive-meta-value">${escapeHtml(String(value || '-'))}</span>
    </div>
  `).join('');
}

function textareaToLines(value) {
  return String(value || '').split(/\r?\n/).map((item) => item.trim()).filter(Boolean);
}

function renderCompetitiveJobStatus(status = {}) {
  const job = status.job || state.competitiveJob?.job || {};
  const latestSuccess = status.latestSuccess || state.competitiveJob?.latestSuccess || {};
  const latestFailure = status.latestFailure || state.competitiveJob?.latestFailure || {};
  const blocks = [];

  const jobStatus = String(job.status || 'idle');
  const jobMessage = job.message || '当前无运行中的竞情生成任务。';
  blocks.push(`
    <div class="competitive-job-card ${escapeHtml(jobStatus)}">
      <div class="competitive-job-title">当前任务</div>
      <div class="competitive-job-value">${escapeHtml(jobMessage)}</div>
      <div class="competitive-job-meta">
        <span>状态：${escapeHtml(jobStatus)}</span>
        ${job.jobId ? `<span>任务ID：${escapeHtml(job.jobId)}</span>` : ''}
        ${job.startedAt ? `<span>开始时间：${escapeHtml(job.startedAt)}</span>` : ''}
        ${job.finishedAt ? `<span>结束时间：${escapeHtml(job.finishedAt)}</span>` : ''}
      </div>
    </div>
  `);

  if (latestSuccess && Object.keys(latestSuccess).length) {
    blocks.push(`
      <div class="competitive-job-card success">
        <div class="competitive-job-title">最近成功</div>
        <div class="competitive-job-value">${escapeHtml(latestSuccess.message || '最近一次生成成功')}</div>
        <div class="competitive-job-meta">
          ${latestSuccess.finishedAt ? `<span>完成时间：${escapeHtml(latestSuccess.finishedAt)}</span>` : ''}
          ${latestSuccess.latestReport?.folder ? `<span>运行目录：${escapeHtml(latestSuccess.latestReport.folder)}</span>` : ''}
          ${latestSuccess.latestReport?.reportFile ? `<span>报告文件：${escapeHtml(latestSuccess.latestReport.reportFile)}</span>` : ''}
        </div>
      </div>
    `);
  }

  if (latestFailure && Object.keys(latestFailure).length) {
    blocks.push(`
      <div class="competitive-job-card failed">
        <div class="competitive-job-title">最近失败</div>
        <div class="competitive-job-value">${escapeHtml(latestFailure.error || latestFailure.message || '失败')}</div>
        <div class="competitive-job-meta">
          ${latestFailure.finishedAt ? `<span>失败时间：${escapeHtml(latestFailure.finishedAt)}</span>` : ''}
        </div>
      </div>
    `);
  }

  return blocks.join('');
}

function renderCompetitiveSettings() {
  const settings = state.competitiveSettings || {};
  const runtime = settings.runtime || {};
  const config = settings.config || {};
  const display = settings.display || {};
  const analysis = settings.analysis || {};
  const notes = Array.isArray(settings.notes) ? settings.notes : [];
  const runtimeEl = $('competitiveSettingsRuntime');
  const tasksEl = $('competitiveSettingsTasks');
  const notesEl = $('competitiveSettingsNotes');

  const bindValue = (id, value, fallback = '') => {
    const el = $(id);
    if (el) el.value = value ?? fallback;
  };

  bindValue('competitiveSearchProvider', 'searxng');
  bindValue('competitiveSearxngBaseUrl', runtime.searxngBaseUrl || '');
  bindValue('competitiveSearxngVerifySsl', String(Boolean(runtime.searxngVerifySsl)));
  bindValue('competitiveOutputFormat', runtime.outputFormat || 'both');
  bindValue('competitiveDeepseekModel', runtime.deepseekModel || 'deepseek-chat');
  bindValue('competitiveQwenModel', runtime.qwenModel || 'qwen-plus');
  bindValue('competitiveFeaturedSectionKeys', Array.isArray(display.featuredSectionKeys) ? display.featuredSectionKeys.join('\n') : '');
  bindValue('competitiveFeaturedSectionLimit', display.featuredSectionLimit ?? 4);
  bindValue('competitiveReportListLimit', display.reportListLimit ?? 12);
  bindValue('competitiveSectionPreviewLimit', display.sectionPreviewLimit ?? 8);
  bindValue('competitiveDefaultReportId', display.defaultReportId || 'latest');
  bindValue('competitiveWindowMode', analysis.windowMode || config.windowMode || '');
  bindValue('competitiveTaskFlow', Array.isArray(analysis.taskFlow) ? analysis.taskFlow.join('\n') : '');
  bindValue('competitiveSeedCompetitors', Array.isArray(analysis.seedCompetitorNames) ? analysis.seedCompetitorNames.join('\n') : '');
  bindValue('competitiveTiantaKeywords', Array.isArray(analysis.tiantaKeywords) ? analysis.tiantaKeywords.join('\n') : '');
  bindValue('competitiveNotesInput', notes.join('\n'));

  if (runtimeEl) {
    runtimeEl.className = 'competitive-settings-grid';
    const runtimeEntries = [
      ['搜索入口', runtime.searchProvider || 'searxng'],
      ['SearXNG 地址', runtime.searxngBaseUrl || '-'],
      ['SSL校验', runtime.searxngVerifySsl ? '开启' : '关闭'],
      ['DeepSeek 模型', runtime.deepseekModel || '-'],
      ['Qwen 模型', runtime.qwenModel || '-'],
      ['输出格式', runtime.outputFormat || '-'],
      ['设置文件', config.settingsFile || '-'],
      ['config.py', config.configPath || '-'],
      ['窗口规则', analysis.windowMode || config.windowMode || '-'],
      ['种子目标数', String((analysis.seedCompetitorNames || []).length || config.seedCompetitorCount || 0)],
    ];
    runtimeEl.innerHTML = runtimeEntries.map(([label, value]) => `
      <div class="competitive-kv-card">
        <div class="competitive-kv-label">${escapeHtml(label)}</div>
        <div class="competitive-kv-value">${escapeHtml(String(value || '-'))}</div>
      </div>
    `).join('');
  }

  if (tasksEl) {
    const taskFlow = Array.isArray(config.taskFlow) ? config.taskFlow : [];
    tasksEl.className = taskFlow.length ? 'competitive-task-list' : 'competitive-task-list empty';
    tasksEl.innerHTML = taskFlow.length
      ? taskFlow.map((task, index) => `
          <div class="competitive-task-item">
            <div class="competitive-task-index">${index + 1}</div>
            <div>
              <div class="competitive-task-title">${escapeHtml(task.label || task.key || '-')}</div>
              <div class="competitive-task-source">${escapeHtml(task.source || '')}</div>
            </div>
          </div>
        `).join('')
      : '暂无数据';
  }

  if (notesEl) {
    notesEl.className = notes.length ? 'competitive-notes' : 'competitive-notes empty';
    notesEl.innerHTML = notes.length
      ? `<ul>${notes.map((note) => `<li>${escapeHtml(note)}</li>`).join('')}</ul>`
      : '暂无数据';
  }
}

async function saveCompetitiveSettings() {
  const payload = {
    runtime: {
      searchProvider: 'searxng',
      searxngBaseUrl: String($('competitiveSearxngBaseUrl')?.value || '').trim(),
      searxngVerifySsl: String($('competitiveSearxngVerifySsl')?.value || 'false') === 'true',
      outputFormat: String($('competitiveOutputFormat')?.value || 'both').trim(),
      llmProvider: 'deepseek',
      deepseekModel: String($('competitiveDeepseekModel')?.value || 'deepseek-chat').trim(),
      qwenModel: String($('competitiveQwenModel')?.value || 'qwen-plus').trim(),
    },
    display: {
      featuredSectionKeys: textareaToLines($('competitiveFeaturedSectionKeys')?.value || ''),
      featuredSectionLimit: Number($('competitiveFeaturedSectionLimit')?.value || 4),
      reportListLimit: Number($('competitiveReportListLimit')?.value || 12),
      sectionPreviewLimit: Number($('competitiveSectionPreviewLimit')?.value || 8),
      defaultReportId: String($('competitiveDefaultReportId')?.value || 'latest').trim() || 'latest',
    },
    analysis: {
      windowMode: String($('competitiveWindowMode')?.value || '').trim(),
      taskFlow: textareaToLines($('competitiveTaskFlow')?.value || ''),
      seedCompetitorNames: textareaToLines($('competitiveSeedCompetitors')?.value || ''),
      tiantaKeywords: textareaToLines($('competitiveTiantaKeywords')?.value || ''),
    },
    notes: textareaToLines($('competitiveNotesInput')?.value || ''),
  };
  const result = await api('/api/competitive-analysis/settings', {
    method: 'PUT',
    body: JSON.stringify(payload),
  });
  state.competitiveSettings = result?.data || payload;
  renderCompetitiveSettings();
  showMessage('竞情分析设置已保存');
}

function renderCompetitiveAnalysis() {
  const status = state.competitiveStatus || {};
  const reports = Array.isArray(state.competitiveReports) ? state.competitiveReports : [];
  const report = state.competitiveReport || null;
  const jobStatus = status?.job?.status || state.competitiveJob?.job?.status || 'idle';
  setText('competitiveStatusBadge', jobStatus === 'running' ? '生成中' : (status?.ready ? '已接入' : '未就绪'));
  setText('competitiveStatusText', status?.message || '竞情分析模块加载中…');
  setText('competitiveReportCount', String(reports.length || 0));
  setText('competitiveSummaryCount', String(Array.isArray(report?.summaryCards) ? report.summaryCards.length : 0));
  setText('competitiveReportTitle', report?.title || '竞情周报正文');

  const jobStatusEl = $('competitiveJobStatus');
  if (jobStatusEl) {
    jobStatusEl.className = 'competitive-job-status';
    jobStatusEl.innerHTML = renderCompetitiveJobStatus(status);
  }

  const runtimeMetaEl = $('competitiveRuntimeMeta');
  if (runtimeMetaEl) {
    runtimeMetaEl.className = 'competitive-runtime-meta';
    runtimeMetaEl.innerHTML = renderCompetitiveStatusMeta(status.runtime || {});
  }

  const railEl = $('competitiveReportRail');
  if (railEl) {
    if (!reports.length) {
      railEl.className = 'competitive-report-rail empty';
      railEl.textContent = '暂无数据';
    } else {
      railEl.className = 'competitive-report-rail';
      railEl.innerHTML = renderCompetitiveReportRail(reports);
      railEl.querySelectorAll('[data-report-id]').forEach((el) => {
        el.addEventListener('click', () => loadCompetitiveReport(el.getAttribute('data-report-id') || ''));
      });
    }
  }

  const summaryEl = $('competitiveSummaryCards');
  if (summaryEl) {
    const cards = Array.isArray(report?.summaryCards) ? report.summaryCards : [];
    summaryEl.className = cards.length ? 'competitive-summary-grid' : 'competitive-summary-grid empty';
    summaryEl.innerHTML = cards.length ? renderCompetitiveSummaryCards(cards) : '暂无数据';
  }

  const metaEl = $('competitiveReportMeta');
  if (metaEl) {
    metaEl.className = report ? 'competitive-report-meta' : 'competitive-report-meta empty';
    metaEl.innerHTML = renderCompetitiveReportMeta(report);
  }

  const sectionsEl = $('competitiveSections');
  if (sectionsEl) {
    const sections = Array.isArray(report?.sections) ? report.sections : [];
    sectionsEl.className = sections.length ? 'competitive-sections' : 'competitive-sections empty';
    sectionsEl.innerHTML = sections.length ? renderCompetitiveSections(sections) : '暂无内容';
  }

  renderCompetitiveSettings();
}

async function loadCompetitiveReport(reportId = '') {
  const path = reportId ? `/api/competitive-analysis/report/${encodeURIComponent(reportId)}` : '/api/competitive-analysis/report/latest';
  const data = await api(path);
  state.competitiveReport = data?.report || null;
  renderCompetitiveAnalysis();
}

async function loadCompetitiveAnalysis() {
  const [status, reports, latest, settings, job] = await Promise.all([
    api('/api/competitive-analysis/status'),
    api('/api/competitive-analysis/reports'),
    api('/api/competitive-analysis/report/latest').catch(() => ({ report: null })),
    api('/api/competitive-analysis/settings'),
    api('/api/competitive-analysis/job').catch(() => ({ job: null })),
  ]);
  state.competitiveStatus = status;
  state.competitiveReports = Array.isArray(reports?.items) ? reports.items : [];
  state.competitiveReport = latest?.report || null;
  state.competitiveSettings = settings || null;
  state.competitiveJob = job || null;
  renderCompetitiveAnalysis();
  scheduleCompetitiveJobRefresh();
}

async function generateCompetitiveAnalysis() {
  const result = await api('/api/competitive-analysis/generate', { method: 'POST' });
  await loadCompetitiveAnalysis();
  scheduleCompetitiveJobRefresh();
  if (result?.accepted) {
    showMessage(result?.message || '竞情分析后台任务已提交');
  } else {
    showMessage(result?.message || '已有后台任务在运行', 'error');
  }
}

function scheduleCompetitiveJobRefresh() {
  clearTimeout(scheduleCompetitiveJobRefresh._timer);
  const status = state.competitiveStatus?.job?.status || state.competitiveJob?.job?.status;
  if (status !== 'running' && status !== 'queued') return;
  scheduleCompetitiveJobRefresh._timer = setTimeout(async () => {
    try {
      await loadCompetitiveAnalysis();
    } catch (error) {
      console.error('competitive job refresh failed', error);
    }
    scheduleCompetitiveJobRefresh();
  }, 20000);
}

async function generateBasic() {
  const btn = $('debugGenerateBtn');
  if (!btn) return;
  
  // Immediate feedback
  btn.disabled = true;
  btn.textContent = '⏳ 生成中，预计3-5分钟...';
  showMessage('正在抓取最新新闻并生成参阅，请稍候...', 'info');
  
  try {
    const result = await api('/api/ceo-brief/generate/free', { method: 'POST' });
    await loadDashboard();
    const newsCount = result.newsCount ?? 0;
    const targetCount = result.targetMatchTotalCount ?? 0;
    showMessage(`✅ 生成完成！产经 ${newsCount} 条，目标匹配 ${targetCount} 条`);
  } catch (error) {
    showMessage(`❌ 生成失败：${error.message || '网络超时，请稍后重试'}`, 'error');
    console.error('generate error:', error);
  } finally {
    btn.disabled = false;
    btn.textContent = '🔧 刷新';
  }
}

async function generateFree() {
  await api('/api/ceo-brief/jobs/generate', { method: 'POST' });
  await loadDashboard();
  showMessage('旧 mock 生成已完成(备用链路)');
}

async function saveSettings() {
  const targetsForm = $('targetsForm');
  const promptsForm = $('promptsForm');

  const targetsPayload = {
    companies: textareaToArray(targetsForm.elements.companies.value),
    industries: textareaToArray(targetsForm.elements.industries.value),
    keywords: textareaToArray(targetsForm.elements.keywords.value),
    regions: textareaToArray(targetsForm.elements.regions.value),
    watchlist: textareaToArray(targetsForm.elements.watchlist.value),
    competitors: textareaToArray(targetsForm.elements.competitors.value),
    upstreamDownstream: textareaToArray(targetsForm.elements.upstreamDownstream.value),
    updatedAt: new Date().toISOString(),
  };

  const promptsPayload = {
    newsFilterPrompt: promptsForm.elements.newsFilterPrompt.value.trim(),
    newsSummaryPrompt: promptsForm.elements.newsSummaryPrompt.value.trim(),
    todoPrompt: promptsForm.elements.todoPrompt.value.trim(),
    updatedAt: new Date().toISOString(),
  };

  await Promise.all([
    api('/api/ceo-brief/settings/targets', {
      method: 'PUT',
      body: JSON.stringify(targetsPayload),
    }),
    api('/api/ceo-brief/settings/prompts', {
      method: 'PUT',
      body: JSON.stringify(promptsPayload),
    }),
  ]);

  state.targets = targetsPayload;
  state.prompts = promptsPayload;
  showMessage('设置已保存');
}

async function resetPrompts() {
  const result = await api('/api/ceo-brief/settings/prompts/reset', { method: 'POST' });
  state.prompts = result.data || {};
  renderSettings();
  showMessage('Prompt 已恢复默认');
}

async function testRssFeeds() {
  const listEl = $('rssStatusList');
  if (!listEl) return;
  listEl.className = 'rss-status-list';
  listEl.textContent = '正在测试 RSS 源...';
  
  try {
    const result = await api('/api/ceo-brief/settings/rss-status');
    const sources = result.sources || [];
    if (!sources.length) {
      listEl.className = 'rss-status-list empty';
      listEl.textContent = '无 RSS 源';
      return;
    }
    
    const validCount = result.valid || 0;
    const invalidCount = result.invalid || 0;
    
    let html = '<div class="rss-status-summary">';
    html += '<span class="valid">✓ 有效 ' + validCount + '</span> &nbsp; ';
    html += '<span class="invalid">✗ 无效 ' + invalidCount + '</span>';
    html += '</div>';
    
    for (const s of sources) {
      const badge = s.valid ? '<span class="badge ok">✓</span>' : '<span class="badge fail">✗</span>';
      html += '<div class="rss-status-row">';
      html += badge;
      html += '<span class="badge">' + (s.type || '') + '</span>';
      html += '<span class="name">' + (s.name || '') + '</span>';
      html += s.valid
        ? '<span class="url">' + (s.url || '') + '</span>'
        : '<span class="error">' + (s.error || '连接失败') + '</span>';
      html += '</div>';
    }
    listEl.className = 'rss-status-list';
    listEl.innerHTML = html;
  } catch (e) {
    listEl.className = 'rss-status-list empty';
    listEl.textContent = '测试失败: ' + (e.message || '网络错误');
  }
}

function setupTabs() {
  ensureIndustryChainTabPlacement();

  const activateTab = (tabName, sourceBtn = null, updateHash = true) => {
    const targetTab = document.getElementById(`tab-${tabName}`);
    if (!targetTab) return;
    const activeBtn = sourceBtn || document.querySelector(`.nav-btn[data-tab="${tabName}"]`);
    document.querySelectorAll('.nav-btn[data-tab]').forEach((item) => item.classList.remove('active'));
    document.querySelectorAll('.tab').forEach((tab) => tab.classList.remove('active'));
    if (activeBtn) activeBtn.classList.add('active');
    targetTab.classList.add('active');
    if (updateHash && window.location.hash !== `#${tabName}`) {
      window.history.replaceState(null, '', `#${tabName}`);
    }
    // 切到企业查询tab时重绘浏览列表（确保可见时渲染）
    if (tabName === 'company-query') {
      renderCompanyQuery();
    }
    if (tabName === 'industry-chain') {
      renderIndustryChain();
      if (currentIndustryChainMode() === 'overview' && !state.industryChainResult) {
        scheduleIndustryChainAnalysis('overview');
      }
    }
  };

  document.querySelectorAll('.nav-btn').forEach((btn) => {
    if (!btn.dataset.tab) return;
    btn.addEventListener('click', () => {
      activateTab(btn.dataset.tab, btn);
    });
  });

  const initialTab = window.location.hash.replace(/^#/, '');
  if (initialTab && document.getElementById(`tab-${initialTab}`)) {
    activateTab(initialTab, null, false);
  }
}

function ensureIndustryChainTabPlacement() {
  let industryTab = $('tab-industry-chain');
  const companyTab = $('tab-company-query');
  if (!industryTab && companyTab) {
    industryTab = document.createElement('section');
    industryTab.id = 'tab-industry-chain';
    industryTab.className = 'tab';
    industryTab.innerHTML = `
      <header class="page-header">
        <div>
          <h2>产业链分析</h2>
          <p class="muted">围绕产业链全景、产业链上下游和被投企业合作机会生成图表与分析报告。</p>
        </div>
      </header>
    `;
    companyTab.insertAdjacentElement('afterend', industryTab);
  }
  if (!industryTab || !companyTab) return;

  const industryBlocks = [
    $('industryChainStatusText')?.closest('.grid'),
    $('industryChainQuestionSection'),
    $('industryChainTables')?.closest('.grid'),
  ].filter(Boolean);
  industryBlocks.forEach((block) => {
    if (block.closest('#tab-company-query')) {
      industryTab.appendChild(block);
    }
  });

  if (!document.querySelector('.nav-btn[data-tab="industry-chain"]')) {
    const companyNav = document.querySelector('.nav-btn[data-tab="company-query"]');
    if (companyNav) {
      const industryNav = document.createElement('button');
      industryNav.className = 'nav-btn';
      industryNav.dataset.tab = 'industry-chain';
      industryNav.type = 'button';
      industryNav.textContent = '产业链分析';
      companyNav.insertAdjacentElement('afterend', industryNav);
    }
  }
}

function setupSortControls() {
  const bindings = [
    ['policySort', 'policy'],
    ['macroSort', 'macro'],
    ['industryFocusSort', 'industryFocus'],
    ['targetSort', 'target'],
  ];
  bindings.forEach(([id, key]) => {
    const el = $(id);
    if (!el) return;
    el.value = state.sortModes[key];
    el.addEventListener('change', () => {
      state.sortModes[key] = el.value;
      renderToday();
    });
  });
}

window.handleNewsCardImageError = handleNewsCardImageError;

async function init() {
  installRuntimeDiagnostics();
  setupTabs();
  setupSortControls();

  bindClick('debugGenerateBtn', '生成中...', generateBasic);
  bindClick('reloadSettingsBtn', '读取中...', loadSettings);
  bindClick('saveSettingsBtn', '保存中...', saveSettings);
  bindClick('resetPromptsBtn', '重置中...', resetPrompts);
  bindClick('testRssBtn', '测试中...', testRssFeeds);
  bindClick('companyQueryStatusBtn', '读取中...', loadCompanyQueryStatus);
  bindClick('companyQuerySearchBtn', '查询中...', () => runCompanyQuerySearch());
  bindDynamicLoadingClick('industryChainInputConfirmBtn', () => {
    const mode = currentIndustryChainMode();
    if (mode === 'graph-qa') return '提问中...';
    if (mode === 'company-updown') return '查询中...';
    if (mode === 'opportunities') return '探索中...';
    return '加载中...';
  }, () => runIndustryChainAnalysis());
  bindClick('industryChainQuestionAnalyzeBtn', '分析中...', () => {
    runIndustryChainQuestionAnalysis().catch((error) => {
      showMessage(error?.message || '分析失败', 'error');
    });
  });
  bindClick('industryChainExportBtn', '导出中...', () => exportIndustryChainReport());
  // 竞情分析已屏蔽
  // bindClick('competitiveAnalysisRefreshBtn', '读取中...', loadCompetitiveAnalysis);
  // bindClick('competitiveAnalysisGenerateBtn', '生成中...', generateCompetitiveAnalysis);
  bindClick('reloadCompetitiveSettingsBtn', '读取中...', loadCompetitiveAnalysis);
  bindClick('saveCompetitiveSettingsBtn', '保存中...', saveCompetitiveSettings);

  const companyQuerySource = $('companyQuerySource');
  if (companyQuerySource) {
    companyQuerySource.addEventListener('change', () => {
      state.companyQuerySource = companyQuerySource.value || 'xlsx';
      if (state.companyQuerySource !== 'xlsx') {
        showMessage('数据库入口当前仅预留，尚未接通。', 'error');
      }
    });
  }

  const companyQueryInput = $('companyQueryInput');
  if (companyQueryInput) {
    companyQueryInput.addEventListener('keydown', (event) => {
      if (event.key === 'Enter') {
        event.preventDefault();
        runCompanyQuerySearch();
      }
    });
  }

  const industryChainMode = $('industryChainMode');
  if (industryChainMode) {
    industryChainMode.addEventListener('change', () => {
      const previousMode = state.industryChainMode || 'overview';
      const previousScope = state.industryChainScope || currentIndustryChainScope();
      rememberIndustryChainInput(previousMode, previousScope);
      state.industryChainMode = industryChainMode.value || 'overview';
      state.industryChainExpandedStages.clear();
      state.industryChainExpandedTracks.clear();
      state.industryChainAllExpanded = false;
      state.industryChainNetworkRequested = false;
      syncIndustryChainControls();
      restoreIndustryChainInput(state.industryChainMode, state.industryChainScope);
      scheduleIndustryChainRender();
      if (state.industryChainMode === 'overview') {
        scheduleIndustryChainAnalysis('overview');
      }
    });
  }

  const industryChainInput = $('industryChainInput');
  if (industryChainInput) {
    industryChainInput.addEventListener('keydown', (event) => {
      if (event.key === 'Enter') {
        event.preventDefault();
        runIndustryChainAnalysis();
      }
    });
  }

  const industryChainScope = $('industryChainScope');
  if (industryChainScope) {
    industryChainScope.addEventListener('change', () => {
      const previousScope = state.industryChainScope || 'external_company';
      rememberIndustryChainInput('opportunities', previousScope);
      state.industryChainScope = industryChainScope.value || 'external_company';
      syncIndustryChainControls();
      restoreIndustryChainInput('opportunities', state.industryChainScope);
      scheduleIndustryChainRender({ skipNetwork: true });
    });
  }

  const industryChainTrackSelect = $('industryChainTrackSelect');
  if (industryChainTrackSelect) {
    industryChainTrackSelect.addEventListener('change', () => {
      state.industryChainSelectedTrackId = industryChainTrackSelect.value || '';
      state.industryChainExpandedStages.clear();
      state.industryChainExpandedTracks.clear();
      state.industryChainAllExpanded = false;
      state.industryChainNetworkRequested = false;
      scheduleIndustryChainRender();
    });
  }

  const industryGraph = $('industryChainGraph');
  if (industryGraph) {
    industryGraph.addEventListener('click', (event) => {
      const expandAllBtn = event.target.closest('[data-industry-expand-all]');
      if (expandAllBtn) {
        state.industryChainAllExpanded = !state.industryChainAllExpanded;
        if (!state.industryChainAllExpanded) {
          state.industryChainExpandedStages.clear();
          state.industryChainExpandedTracks.clear();
        }
        scheduleIndustryChainRender({ skipNetwork: true });
        return;
      }
      const companyBtn = event.target.closest('[data-industry-company]');
      if (companyBtn) {
        const company = companyBtn.getAttribute('data-industry-company') || '';
        const modeSelect = $('industryChainMode');
        const input = $('industryChainInput');
        if (modeSelect) modeSelect.value = 'company-updown';
        if (input) input.value = company;
        state.industryChainMode = 'company-updown';
        syncIndustryChainControls();
        runIndustryChainAnalysis('company-updown');
        return;
      }
      const trackBtn = event.target.closest('[data-industry-track-id]');
      if (trackBtn) {
        const trackId = trackBtn.getAttribute('data-industry-track-id') || '';
        if (trackId) {
          if (state.industryChainExpandedTracks.has(trackId)) {
            state.industryChainExpandedTracks.delete(trackId);
          } else {
            state.industryChainExpandedTracks.add(trackId);
          }
          scheduleIndustryChainRender({ skipNetwork: true });
        }
        return;
      }
      const stageBtn = event.target.closest('[data-industry-stage-id]');
      if (stageBtn) {
        const stageId = stageBtn.getAttribute('data-industry-stage-id') || '';
        if (stageId) {
          if (state.industryChainExpandedStages.has(stageId)) {
            state.industryChainExpandedStages.delete(stageId);
          } else {
            state.industryChainExpandedStages.add(stageId);
          }
          scheduleIndustryChainRender({ skipNetwork: true });
        }
        return;
      }
    });
  }

  const industryNetwork = $('industryChainNetwork');
  if (industryNetwork) {
    industryNetwork.addEventListener('click', (event) => {
      const showBtn = event.target.closest('#industryChainShowNetworkBtn');
      if (!showBtn) return;
      if (!state.industryChainResult?.graph) {
        showMessage('暂无可渲染的产业链图谱', 'error');
        return;
      }
      state.industryChainNetworkRequested = true;
      showBtn.disabled = true;
      showBtn.textContent = '渲染中...';
      requestAnimationFrame(() => renderIndustryChainNetwork(state.industryChainResult.graph));
    });
  }

  const relationSummary = $('industryChainRelationSummary');
  if (relationSummary) {
    relationSummary.addEventListener('scroll', (event) => {
      const wrap = event.target.closest('.industry-chain-relation-scroll');
      if (!wrap) return;
      if (wrap.scrollTop + wrap.clientHeight < wrap.scrollHeight - 24) return;
      const total = state.industryChainResult?.tables?.[0]?.rows?.length || 0;
      const nextCount = Math.min(total, (Number(state.industryChainRelationVisibleCount) || 10) + 10);
      if (nextCount <= state.industryChainRelationVisibleCount) return;
      state.industryChainRelationVisibleCount = nextCount;
      scheduleIndustryChainRender({ skipNetwork: true });
    }, true);
  }

  const industryChainQuestion = $('industryChainQuestion');
  if (industryChainQuestion) {
    industryChainQuestion.addEventListener('keydown', (event) => {
      if (event.key === 'Enter') {
        event.preventDefault();
        runIndustryChainQuestionAnalysis();
      }
    });
  }

  const historyWrap = $('companyQueryHistory');
  if (historyWrap) {
    historyWrap.addEventListener('click', (event) => {
      const btn = event.target.closest('[data-company-query-history]');
      if (!btn) return;
      const query = btn.getAttribute('data-company-query-history') || '';
      runCompanyQuerySearch(query);
    });
  }

  bindClick('reloadMarkdownBtn', '读取中...', async () => {
    showMessage('刷新中...请手动刷新页面');
  });
  bindClick('saveNoteBtn', '保存中...', async () => saveSelectedNote());
  bindClick('deleteNoteBtn', '删除中...', async () => deleteSelectedNote());

  const prevBtn = $('calendarPrevBtn');
  if (prevBtn) prevBtn.addEventListener('click', () => {
    const base = state.noteCalendarCursor || new Date();
    state.noteCalendarCursor = new Date(base.getFullYear(), base.getMonth() - 1, 1);
    renderCalendar();
  });
  const nextBtn = $('calendarNextBtn');
  if (nextBtn) nextBtn.addEventListener('click', () => {
    const base = state.noteCalendarCursor || new Date();
    state.noteCalendarCursor = new Date(base.getFullYear(), base.getMonth() + 1, 1);
    renderCalendar();
  });

  const dashboardResult = await loadDashboard().then(() => null).catch((error) => error);
  const settingsResult = await loadSettings().then(() => null).catch((error) => error);
  const companyQueryResult = await loadCompanyQueryStatus().then(() => null).catch((error) => error);
  const industryChainResult = await loadIndustryChainStatus().then(() => null).catch((error) => error);
  // 竞情分析已屏蔽
  const competitiveResult = null;

  // 数据加载后延迟重绘企业浏览（确保DOM就绪），多次尝试确保生效
  const retryRender = () => {
    if (state.companyBrowseItems.length) {
      renderCompanyQuery();
      console.log('[company-browse] rendered, items:', state.companyBrowseItems.length);
    }
  };
  setTimeout(retryRender, 300);
  setTimeout(retryRender, 1000);

  if (dashboardResult || settingsResult || companyQueryResult || industryChainResult || competitiveResult) {
    console.error(dashboardResult || settingsResult || companyQueryResult || industryChainResult || competitiveResult);
    if (dashboardResult) {
      renderHealth(null);
      showMessage(`首页加载有部分失败:${dashboardResult.message}`, 'error');
    } else if (settingsResult) {
      showMessage(`设置页加载有部分失败:${settingsResult.message}`, 'error');
    } else if (companyQueryResult) {
      showMessage(`企业查询加载有部分失败:${companyQueryResult.message}`, 'error');
    } else if (industryChainResult) {
      showMessage(`产业链分析加载有部分失败:${industryChainResult.message}`, 'error');
    } else {
      showMessage(`竞情分析加载有部分失败:${competitiveResult.message}`, 'error');
    }
  }
}

init();
