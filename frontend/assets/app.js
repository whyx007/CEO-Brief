const state = {
  today: null,
  latestRun: null,
  latestBrief: null,
  marketSnapshot: null,
  fxSnapshot: null,
  targets: null,
  prompts: null,
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
        strictNoticeEl.textContent = '今日未检索到符合当前目标条件的高相关结果。系统已启用严格匹配,未再回退展示泛商业新闻。建议扩大目标词、补充竞对/产业链词,或增强航天相关召回 query。';
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

    const watchlistTagsEl = $('targetWatchlistTags');
    if (watchlistTagsEl) {
      const watchlist = Array.isArray(data?.meta?.targetWatchlist) ? data.meta.targetWatchlist : [];
      watchlistTagsEl.innerHTML = watchlist.map((tag) => `<span class="tag">${escapeHtml(tag)}</span>`).join('');
    }

    renderNewsList('targetList', 'targetCount', data.targetUpdates, (items) => renderReaderList(items, {
      sortMode: state.sortModes.target,
      showTags: true,
      preferImageFirst: true,
      tagFilter: (tag) => !['客户动态', '竞争对手动态', '目标', '行业机会', '中科天塔动态'].includes(tag),
    }));

    renderNewsList('todoList', 'todoCount', data.todoItems, (items) => items.map((item) => `
      <div class="card-item">
        <h4>${escapeHtml(item?.content || '-')}</h4>
        <div class="card-meta">
          <span class="priority ${escapeHtml((item?.priority || 'low').toLowerCase())}">${escapeHtml(item?.priority || 'low')}</span>
        </div>
        ${item?.reason ? `<div class="card-summary">触发原因:${escapeHtml(item.reason)}</div>` : ''}
      </div>
    `).join(''));

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
  if (containerId === 'todoList') setText('todoCountBottom', String(list.length));
  const container = $(containerId);
  if (!container) return;
  if (!list.length) {
    container.className = containerId === 'todoList' ? 'note-ai-list empty' : 'list reader-list empty';
    container.textContent = '暂无数据';
    return;
  }
  container.className = containerId === 'todoList' ? 'note-ai-list' : 'list reader-list';
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

function renderLatestRun() {
  return;
}

function renderLatestBrief() {
  const el = $('latestBriefMarkdown');
  if (!el) return;
  el.textContent = state.latestBrief?.content || '暂无内容';
  el.className = state.latestBrief?.content ? 'markdown-preview' : 'markdown-preview empty';
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
    ['companies', 'industries', 'keywords', 'regions', 'competitors', 'upstreamDownstream'].forEach((key) => {
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
  const [health, today, latestRun, latestBrief] = await Promise.all([
    api('/health').catch(() => null),
    api('/api/ceo-brief/today').catch(() => null),
    api('/api/ceo-brief/latest-run').catch(() => null),
    api('/api/ceo-brief/latest-brief').catch(() => null),
  ]);

  renderHealth(health);
  state.today = today || {};
  state.latestRun = latestRun;
  state.latestBrief = latestBrief;
  renderToday();
  renderLatestRun();
  renderLatestBrief();

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

async function generateBasic() {
  const result = await api('/api/ceo-brief/generate/free', { method: 'POST' });
  await loadDashboard();
  showMessage(`今日参阅生成完成,共 ${result.newsCount ?? 0} 条新闻`);
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

function setupTabs() {
  document.querySelectorAll('.nav-btn').forEach((btn) => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.nav-btn').forEach((item) => item.classList.remove('active'));
      document.querySelectorAll('.tab').forEach((tab) => tab.classList.remove('active'));
      btn.classList.add('active');
      document.getElementById(`tab-${btn.dataset.tab}`).classList.add('active');
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

  bindClick('refreshBtn', '刷新中...', loadDashboard);
  bindClick('generateBtn', '生成中...', generateBasic);
  bindClick('reloadSettingsBtn', '读取中...', loadSettings);
  bindClick('saveSettingsBtn', '保存中...', saveSettings);
  bindClick('resetPromptsBtn', '重置中...', resetPrompts);
  bindClick('reloadMarkdownBtn', '读取中...', async () => {
    state.latestBrief = await api('/api/ceo-brief/latest-brief');
    renderLatestBrief();
    showMessage('Markdown 正文已刷新');
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

  if (dashboardResult || settingsResult) {
    console.error(dashboardResult || settingsResult);
    if (dashboardResult) {
      renderHealth(null);
      showMessage(`首页加载有部分失败:${dashboardResult.message}`, 'error');
    } else {
      showMessage(`设置页加载有部分失败:${settingsResult.message}`, 'error');
    }
  }
}

init();
