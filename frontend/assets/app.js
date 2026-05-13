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
  const res = await fetch(path, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  const text = await res.text();
  const data = text ? JSON.parse(text) : null;
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

function renderHealth(health) {
  const ok = Boolean(health?.ok);
  setText('healthText', ok ? '服务状态:在线' : '服务状态:不可用');
  const provider = health?.llmProvider || '-';
  const model = health?.llmModel || '-';
  const enabled = health?.deepseekEnabled ? '已启用' : '未启用';
  const metaEl = $('backendMetaText');
  if (metaEl) {
    metaEl.textContent = ok
      ? `LLM:${provider} / ${model} · DeepSeek:${enabled}`
      : '运行信息:读取失败';
  }
}

function setLoading(button, loadingText, fn) {
  return async () => {
    const old = button.textContent;
    button.disabled = true;
    button.textContent = loadingText;
    try {
      await fn();
    } finally {
      button.disabled = false;
      button.textContent = old;
    }
  };
}

function renderToday() {
  try {
    const data = state.today || {};
    const meta = data.meta || {};
    const strictEmpty = Boolean(meta.strictMode) && (meta.strictMatchCount ?? data.industrialNews?.length ?? 0) === 0;

    const llmSummaryEl = $('llmSummary');
    if (llmSummaryEl) {
      const llmSummary = String(data.llmSummary || '').trim();
      llmSummaryEl.textContent = llmSummary || '暂无内容';
      llmSummaryEl.className = llmSummary ? 'markdown-block' : 'markdown-block empty';
    }

    const strictNoticeEl = $('strictModeNotice');
    if (strictNoticeEl) {
      if (strictEmpty) {
        strictNoticeEl.className = 'message error';
        strictNoticeEl.textContent = '严格匹配已启用，当前无高相关结果。';
      } else if (meta.strictMode) {
        strictNoticeEl.className = 'message success';
        strictNoticeEl.textContent = `严格匹配已启用:高相关 ${meta.strictMatchCount ?? (data.industrialNews?.length || 0)} 条,政策 ${meta.policyMatchCount ?? 0} 条,竞对/产业链 ${meta.competitorMatchCount ?? 0} 条。`;
      } else {
        strictNoticeEl.className = 'message hidden';
        strictNoticeEl.textContent = '';
      }
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
  const [health, today] = await Promise.all([
    api('/health').catch(() => null),
    api('/api/ceo-brief/today').catch(() => null),
  ]);

  renderHealth(health);
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
  document.querySelectorAll('.nav-btn').forEach((btn) => {
    if (!btn.dataset.tab) return;
    btn.addEventListener('click', () => {
      const targetTab = document.getElementById(`tab-${btn.dataset.tab}`);
      if (!targetTab) return;
      document.querySelectorAll('.nav-btn[data-tab]').forEach((item) => item.classList.remove('active'));
      document.querySelectorAll('.tab').forEach((tab) => tab.classList.remove('active'));
      btn.classList.add('active');
      targetTab.classList.add('active');
      // 切到企业查询tab时重绘浏览列表（确保可见时渲染）
      if (btn.dataset.tab === 'company-query') {
        renderCompanyQuery();
      }
    });
  });
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
      if ((event.ctrlKey || event.metaKey) && event.key === 'Enter') {
        event.preventDefault();
        runCompanyQuerySearch();
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

  if (dashboardResult || settingsResult || companyQueryResult || competitiveResult) {
    console.error(dashboardResult || settingsResult || companyQueryResult || competitiveResult);
    if (dashboardResult) {
      renderHealth(null);
      showMessage(`首页加载有部分失败:${dashboardResult.message}`, 'error');
    } else if (settingsResult) {
      showMessage(`设置页加载有部分失败:${settingsResult.message}`, 'error');
    } else if (companyQueryResult) {
      showMessage(`企业查询加载有部分失败:${companyQueryResult.message}`, 'error');
    } else {
      showMessage(`竞情分析加载有部分失败:${competitiveResult.message}`, 'error');
    }
  }
}

init();
