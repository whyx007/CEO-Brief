const state = {
  today: null,
  latestRun: null,
  latestBrief: null,
  targets: null,
  prompts: null,
};

const $ = (id) => document.getElementById(id);

function showMessage(text, type = 'success') {
  const el = $('globalMessage');
  el.textContent = text;
  el.className = `message ${type}`;
  clearTimeout(showMessage._timer);
  showMessage._timer = setTimeout(() => {
    el.className = 'message hidden';
    el.textContent = '';
  }, 3500);
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

function renderHealth(health) {
  const ok = Boolean(health?.ok);
  $('healthText').textContent = ok ? '服务状态：在线' : '服务状态：不可用';
  const provider = health?.llmProvider || '-';
  const model = health?.llmModel || '-';
  const enabled = health?.deepseekEnabled ? '已启用' : '未启用';
  const metaEl = $('backendMetaText');
  if (metaEl) {
    metaEl.textContent = ok
      ? `LLM：${provider} / ${model} · DeepSeek：${enabled}`
      : '运行信息：读取失败';
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
  const data = state.today || {};
  const meta = data.meta || {};
  const strictEmpty = Boolean(meta.strictMode) && (meta.strictMatchCount ?? data.industrialNews?.length ?? 0) === 0;
  $('briefDate').textContent = data.date || '-';
  $('briefStatus').textContent = data.status || '-';
  $('briefGeneratedAt').textContent = data.generatedAt || '-';
  $('briefMode').textContent = meta.mode || '-';
  $('briefGenerator').textContent = meta.generatedBy || '-';
  $('briefNewsCount').textContent = String(
    meta.newsCount
    ?? ((data.policyNews?.length || 0) + (data.macroEconomicNews?.length || 0) + (data.industryFocusNews?.length || 0) + (data.competitorNews?.length || 0))
  );
  $('llmSummary').textContent = data.llmSummary || '暂无内容';

  const strictNoticeEl = $('strictModeNotice');
  if (strictNoticeEl) {
    if (strictEmpty) {
      strictNoticeEl.className = 'message error';
      strictNoticeEl.textContent = '今日未检索到符合当前目标条件的高相关结果。系统已启用严格匹配，未再回退展示泛商业新闻。建议扩大目标词、补充竞对/产业链词，或增强航天相关召回 query。';
    } else if (meta.strictMode) {
      strictNoticeEl.className = 'message success';
      strictNoticeEl.textContent = `严格匹配已启用：高相关 ${meta.strictMatchCount ?? (data.industrialNews?.length || 0)} 条，政策 ${meta.policyMatchCount ?? 0} 条，竞对/产业链 ${meta.competitorMatchCount ?? 0} 条。`;
    } else {
      strictNoticeEl.className = 'message hidden';
      strictNoticeEl.textContent = '';
    }
  }

  const weather = data.weather;
  $('weatherBlock').innerHTML = weather
    ? `
      <div class="weather-main">
        <div>
          <div class="label">${escapeHtml(weather.location || '未知地点')}</div>
          <div class="weather-temp">${escapeHtml(weather.condition || '-')}</div>
        </div>
        <div class="weather-temp">${escapeHtml(weather.temperatureMin ?? '-')}° ~ ${escapeHtml(weather.temperatureMax ?? '-')}°</div>
      </div>
      <div class="muted">${escapeHtml(weather.advice || '')}</div>
    `
    : '暂无内容';

  renderNewsList('policyList', 'policyCount', data.policyNews, (item) => `
    <div class="card-item">
      <h4>${escapeHtml(item.title)}</h4>
      <div class="card-meta">
        <span>${escapeHtml(item.source || '未知来源')}</span>
        <span>${escapeHtml(item.publishedAt || '')}</span>
      </div>
      <div class="card-summary">${escapeHtml(stripHtml(item.summary || ''))}</div>
      ${item.url ? `<div class="tags"><a class="tag link-tag" href="${escapeHtml(item.url)}" target="_blank" rel="noreferrer noopener">查看原文</a></div>` : ''}
    </div>
  `);

  renderNewsList('macroList', 'macroCount', data.macroEconomicNews, (item) => `
    <div class="card-item">
      <h4>${escapeHtml(item.title)}</h4>
      <div class="card-meta">
        <span>${escapeHtml(item.source || '未知来源')}</span>
        <span>${escapeHtml(item.publishedAt || '')}</span>
      </div>
      <div class="card-summary">${escapeHtml(stripHtml(item.summary || ''))}</div>
      ${item.url ? `<div class="tags"><a class="tag link-tag" href="${escapeHtml(item.url)}" target="_blank" rel="noreferrer noopener">查看原文</a></div>` : ''}
    </div>
  `);

  renderNewsList('industryFocusList', 'industryFocusCount', data.industryFocusNews, (item) => `
    <div class="card-item">
      <h4>${escapeHtml(item.title)}</h4>
      <div class="card-meta">
        <span>${escapeHtml(item.source || '未知来源')}</span>
        <span>${escapeHtml(item.publishedAt || '')}</span>
        ${item.relevanceScore != null ? `<span>相关度 ${escapeHtml(item.relevanceScore)}</span>` : ''}
      </div>
      <div class="card-summary">${escapeHtml(stripHtml(item.summary || ''))}</div>
      ${item.matchedTargets?.length ? `<div class="tags">${item.matchedTargets.map((tag) => `<span class="tag">${escapeHtml(tag)}</span>`).join('')}</div>` : ''}
      ${item.relevanceReason ? `<div class="card-summary" style="margin-top:10px; color:#bcd0ff;">命中依据：${escapeHtml(item.relevanceReason)}</div>` : ''}
      ${item.url ? `<div class="tags"><a class="tag link-tag" href="${escapeHtml(item.url)}" target="_blank" rel="noreferrer noopener">查看原文</a></div>` : ''}
    </div>
  `);

  renderNewsList('targetList', 'targetCount', data.targetUpdates, (item) => `
    <div class="card-item">
      <h4>${escapeHtml(item.title)}</h4>
      <div class="card-meta">
        <span>${escapeHtml(item.source || '未知来源')}</span>
        <span>${escapeHtml(item.publishedAt || '')}</span>
      </div>
      <div class="card-summary">${escapeHtml(item.summary || '')}</div>
      <div class="tags">${(item.matchedTargets || []).map((tag) => `<span class="tag">${escapeHtml(tag)}</span>`).join('')}</div>
      ${item.relevanceReason ? `<div class="card-summary" style="margin-top:10px; color:#bcd0ff;">关注理由：${escapeHtml(item.relevanceReason)}</div>` : ''}
    </div>
  `);

  renderNewsList('todoList', 'todoCount', data.todoItems, (item) => `
    <div class="card-item">
      <h4>${escapeHtml(item.content)}</h4>
      <div class="card-meta">
        <span class="priority ${escapeHtml((item.priority || 'low').toLowerCase())}">${escapeHtml(item.priority || 'low')}</span>
      </div>
      ${item.reason ? `<div class="card-summary">触发原因：${escapeHtml(item.reason)}</div>` : ''}
    </div>
  `);
}

function renderNewsList(containerId, countId, items, renderItem) {
  const list = Array.isArray(items) ? items : [];
  $(countId).textContent = String(list.length);
  const container = $(containerId);
  if (!list.length) {
    container.className = 'list empty';
    container.textContent = '暂无数据';
    return;
  }
  container.className = 'list';
  container.innerHTML = list.map(renderItem).join('');
}

function renderLatestRun() {
  const latest = state.latestRun;
  $('latestRunText').textContent = latest
    ? `${latest.status || '-'} · ${latest.date || '-'} · ${latest.generatedAt || '-'}${latest.mode ? ` · ${latest.mode}` : ''}`
    : '-';
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
  ['companies', 'industries', 'keywords', 'regions', 'competitors', 'upstreamDownstream'].forEach((key) => {
    if (targetsForm.elements[key]) {
      targetsForm.elements[key].value = arrayToTextarea(targets[key]);
    }
  });

  const promptsForm = $('promptsForm');
  ['newsFilterPrompt', 'newsSummaryPrompt', 'todoPrompt'].forEach((key) => {
    if (promptsForm.elements[key]) {
      promptsForm.elements[key].value = prompts[key] || '';
    }
  });
}

async function loadDashboard() {
  const [health, today, latestRun, latestBrief] = await Promise.all([
    api('/health').catch(() => null),
    api('/api/ceo-brief/today'),
    api('/api/ceo-brief/latest-run').catch(() => null),
    api('/api/ceo-brief/latest-brief').catch(() => null),
  ]);
  renderHealth(health);
  state.today = today;
  state.latestRun = latestRun;
  state.latestBrief = latestBrief;
  renderToday();
  renderLatestRun();
  renderLatestBrief();
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
  showMessage(`今日参阅生成完成，共 ${result.newsCount ?? 0} 条新闻`);
}

async function generateFree() {
  await api('/api/ceo-brief/jobs/generate', { method: 'POST' });
  await loadDashboard();
  showMessage('旧 mock 生成已完成（备用链路）');
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

async function init() {
  setupTabs();

  $('refreshBtn').addEventListener('click', setLoading($('refreshBtn'), '刷新中…', loadDashboard));
  $('generateBtn').addEventListener('click', setLoading($('generateBtn'), '生成中…', generateBasic));
  $('generateFreeBtn').addEventListener('click', setLoading($('generateFreeBtn'), '生成中…', generateFree));
  $('reloadSettingsBtn').addEventListener('click', setLoading($('reloadSettingsBtn'), '读取中…', loadSettings));
  $('saveSettingsBtn').addEventListener('click', setLoading($('saveSettingsBtn'), '保存中…', saveSettings));
  $('resetPromptsBtn').addEventListener('click', setLoading($('resetPromptsBtn'), '重置中…', resetPrompts));
  $('reloadMarkdownBtn').addEventListener('click', setLoading($('reloadMarkdownBtn'), '读取中…', async () => {
    state.latestBrief = await api('/api/ceo-brief/latest-brief');
    renderLatestBrief();
    showMessage('Markdown 正文已刷新');
  }));

  try {
    await Promise.all([loadDashboard(), loadSettings()]);
  } catch (error) {
    console.error(error);
    renderHealth(null);
    showMessage(`初始化失败：${error.message}`, 'error');
  }
}

init();
