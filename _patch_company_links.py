# -*- coding: utf-8 -*-
from pathlib import Path

path = Path(r'C:\Users\Administrator\.openclaw\workspace\finance-postinvest-ai-platform\ceo-brief\frontend\assets\app.js')
text = path.read_text(encoding='utf-8')
start = text.index('function companyField(raw, key, fallback =')
end = text.index('function renderCompanyQueryResults(items) {')
replacement = '''function companyField(raw, key, fallback = '—') {
  const value = raw && typeof raw === 'object' ? raw[key] : '';
  return escapeHtml(value || fallback);
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

function renderCompanyProfileCard(item) {
  const raw = item?.raw || {};
  const title = escapeHtml(item?.title || raw['公司名称'] || '未命名企业');
  const websiteUrl = companyWebsiteUrl(item);
  const titleLink = websiteUrl && websiteUrl !== '#'
    ? `<a class="company-name-link" href="${escapeHtml(websiteUrl)}" target="_blank" rel="noreferrer noopener">${title}</a>`
    : `<span class="company-name-link disabled">${title}</span>`;
  const tech = companyField(raw, '核心技术');
  const product = companyField(raw, '产品');
  const maturity = companyField(raw, '技术成熟度');
  const industry = companyField(raw, '产品应用行业');
  const customers = companyField(raw, '客户');
  const suppliers = companyField(raw, '供应商');
  const scene = companyField(raw, '应用场景');
  const futureScene = companyField(raw, '可能应用场景');
  const model = companyField(raw, '商务模式');
  const delivery = companyField(raw, '交付能力');
  const certs = companyField(raw, '认证/资质/知识产权');
  const team = companyField(raw, '创始团队与短板');
  const resources = companyField(raw, '当前最需要的资源类型');
  const revenue = companyField(raw, '近三年营收及利润');
  const competition = companyField(raw, '竞对及技术差异');
  const matchLevel = companyField(raw, '匹配程度');
  const tags = Array.isArray(item?.matchedTargets)
    ? item.matchedTargets.filter((tag) => tag && tag !== '企业查询').slice(0, 4)
    : [];

  return `
    <article class="company-profile-card">
      <div class="company-profile-head">
        <div>
          <h4>${titleLink}</h4>
          <div class="card-meta compact"><span>企业画像</span><span>${escapeHtml(item?.source || 'company-info.xlsx')}</span></div>
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

'''
text = text[:start] + replacement + text[end:]
path.write_text(text, encoding='utf-8')
print('patched app.js')
