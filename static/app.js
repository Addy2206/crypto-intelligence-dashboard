/* ─────────────────────────────────────────────────────────────────────────
   CIPHER — app.js
   Client-side router + all page logic
   ───────────────────────────────────────────────────────────────────────── */

// ── API URL: works on localhost AND on Render ──────────────────────────────
const API = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
  ? 'http://localhost:5000/api'
  : '/api';   // relative URL — same origin on Render

// ── Coin metadata (mirrors backend) ───────────────────────────────────────
const COINS_META = {
  bitcoin:     {symbol:'BTC', name:'Bitcoin',  logo:'https://cryptologos.cc/logos/bitcoin-btc-logo.png',    color:'#f0a500'},
  ethereum:    {symbol:'ETH', name:'Ethereum', logo:'https://cryptologos.cc/logos/ethereum-eth-logo.png',   color:'#627eea'},
  binancecoin: {symbol:'BNB', name:'BNB',      logo:'https://cryptologos.cc/logos/binancecoin-bnb-logo.png',color:'#f3ba2f'},
  solana:      {symbol:'SOL', name:'Solana',   logo:'https://cryptologos.cc/logos/solana-sol-logo.png',     color:'#9945ff'},
  ripple:      {symbol:'XRP', name:'XRP',      logo:'https://cryptologos.cc/logos/xrp-xrp-logo.png',       color:'#3bcefc'},
  cardano:     {symbol:'ADA', name:'Cardano',  logo:'https://cryptologos.cc/logos/cardano-ada-logo.png',    color:'#0052cc'},
  avalanche:   {symbol:'AVAX',name:'Avalanche',logo:'https://cryptologos.cc/logos/avalanche-avax-logo.png', color:'#e84142'},
  dogecoin:    {symbol:'DOGE',name:'Dogecoin', logo:'https://cryptologos.cc/logos/dogecoin-doge-logo.png',  color:'#c2a633'},
  polkadot:    {symbol:'DOT', name:'Polkadot', logo:'https://cryptologos.cc/logos/polkadot-new-dot-logo.png',color:'#e6007a'},
  chainlink:   {symbol:'LINK',name:'Chainlink',logo:'https://cryptologos.cc/logos/chainlink-link-logo.png', color:'#2a5ada'},
  shiba_inu:   {symbol:'SHIB',name:'Shiba Inu',logo:'https://cryptologos.cc/logos/shiba-inu-shib-logo.png', color:'#ffa409'},
  near:        {symbol:'NEAR',name:'NEAR',     logo:'https://cryptologos.cc/logos/near-protocol-near-logo.png',color:'#00c08b'},
};

// ── State ──────────────────────────────────────────────────────────────────
let pricesData  = {};
let histChart   = null;
let cmpChart    = null;
let selHistCoin = 'bitcoin';
let selMsCoin   = 'bitcoin';
let cmpCoins    = new Set(['bitcoin','ethereum','solana']);
let cmpPeriod   = '365';
let dashboardLoaded   = false;
let moversLoaded      = false;
let newsLoaded        = false;
let dashRefreshTimer  = null;
let lessonsDone       = new Set(JSON.parse(localStorage.getItem('cipher_lessons') || '[]'));

// ── Formatters ─────────────────────────────────────────────────────────────
function fmt(n) {
  if (n == null || isNaN(n)) return '—';
  if (n >= 1e9)  return '$' + (n / 1e9).toFixed(2) + 'B';
  if (n >= 1e6)  return '$' + (n / 1e6).toFixed(2) + 'M';
  if (n >= 1000) return '$' + n.toLocaleString('en-US', {maximumFractionDigits: 2});
  return '$' + n.toFixed(n < 1 ? 6 : 2);
}
function fmtPct(n) {
  if (n == null || isNaN(n)) return '—';
  return (n >= 0 ? '+' : '') + n.toFixed(2) + '%';
}
function pctCls(n) { return (n >= 0) ? 'up' : 'down'; }

// ── API helper ─────────────────────────────────────────────────────────────
async function api(path) {
  const r = await fetch(API + path);
  if (!r.ok) throw new Error('API ' + r.status);
  return r.json();
}

// ══════════════════════════════════════════════════════════════════════════
// ROUTER
// ══════════════════════════════════════════════════════════════════════════
function navigate(page) {
  // Hide all pages
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  // Show target
  const el = document.getElementById('page-' + page);
  if (el) el.classList.add('active');
  // Update nav buttons
  document.querySelectorAll('.nav-btn, .mob-btn').forEach(b => {
    b.classList.toggle('active', b.dataset.page === page);
  });
  // Lazy load content per page
  if (page === 'dashboard' && !dashboardLoaded) {
    dashboardLoaded = true;
    initDashboard();
  }
  if (page === 'news' && !newsLoaded) {
    newsLoaded = true;
    loadNews();
  }
  if (page === 'movers' && !moversLoaded) {
    moversLoaded = true;
    loadMovers();
  }
  if (page === 'learn') {
    renderLearnProgress();
  }
  // Clear auto-refresh when leaving dashboard
  if (page !== 'dashboard' && dashRefreshTimer) {
    clearInterval(dashRefreshTimer);
    dashRefreshTimer = null;
  }
  // Scroll top
  window.scrollTo({top: 0, behavior: 'smooth'});
}

// ══════════════════════════════════════════════════════════════════════════
// THEME
// ══════════════════════════════════════════════════════════════════════════
function applyTheme(theme) {
  document.documentElement.setAttribute('data-theme', theme);
  const label = document.getElementById('switchLabel');
  if (label) label.textContent = theme === 'dark' ? '☀️' : '🌙';
}

function toggleTheme() {
  const current = document.documentElement.getAttribute('data-theme') || 'dark';
  const next = current === 'dark' ? 'light' : 'dark';
  applyTheme(next);
  localStorage.setItem('cipher_theme', next);
}

// ══════════════════════════════════════════════════════════════════════════
// MOBILE NAV
// ══════════════════════════════════════════════════════════════════════════
function toggleMobileNav() {
  document.getElementById('mobileNav').classList.toggle('open');
}
function closeMobileNav() {
  document.getElementById('mobileNav').classList.remove('open');
}

// ══════════════════════════════════════════════════════════════════════════
// MOOD RESPONSES (Home)
// ══════════════════════════════════════════════════════════════════════════
const MOOD_RESPONSES = {
  curious: "Great place to start! Head to <strong>📚 Learn</strong> for a step-by-step introduction, or check <strong>🤔 Why Crypto?</strong> to understand the big picture.",
  confused: "Don't worry — crypto is confusing for everyone at first. Start with <strong>📚 Learn</strong>, lesson 1: What is Money? We've written everything in plain English.",
  excited: "Exciting times! Before you invest anything, check <strong>📚 Learn</strong> lesson 6 (Benefits & Risks) and lesson 7 (Common Mistakes). Knowledge is your best protection.",
  nervous: "That's a healthy reaction. Crypto carries real risk. Read <strong>🤔 Why Crypto?</strong> for an honest picture of benefits AND risks before making any decisions.",
};

function setMood(mood) {
  document.querySelectorAll('.mood-btn').forEach(b =>
    b.style.borderColor = b.textContent.toLowerCase().includes(mood.replace('curious','curious').split(' ')[0]) ? 'var(--cyan)' : ''
  );
  const r = document.getElementById('moodResponse');
  r.innerHTML = MOOD_RESPONSES[mood] || '';
  r.style.opacity = '0';
  requestAnimationFrame(() => { r.style.transition = 'opacity .4s'; r.style.opacity = '1'; });
}

// ══════════════════════════════════════════════════════════════════════════
// NEWS PAGE
// ══════════════════════════════════════════════════════════════════════════
async function loadNews() {
  const container = document.getElementById('newsContainer');
  try {
    const data = await api('/news');
    const articles = data.articles || [];
    if (!articles.length) {
      container.innerHTML = '<div class="err">No news articles available right now.</div>';
      return;
    }
    container.innerHTML = `<div class="news-grid">${articles.map(a => `
      <div class="news-card">
        <div class="news-card-hdr">
          <a class="news-title" href="${a.link}" target="_blank" rel="noopener">${escHtml(a.title)}</a>
          <span class="news-date">${formatNewsDate(a.date)}</span>
        </div>
        ${a.summary ? `<p class="news-summary">${escHtml(a.summary)}</p>` : ''}
        <div class="news-why">💡 Why it matters: crypto markets react quickly to news — prices can move within minutes of major headlines.</div>
        ${a.link && a.link !== '#' ? `<a class="news-read-more" href="${a.link}" target="_blank" rel="noopener">Read full article →</a>` : ''}
      </div>`).join('')}
    </div>`;
  } catch(e) {
    container.innerHTML = `<div class="err">⚠ Could not load news. Please check your connection.<br><br>${e.message}</div>`;
  }
}

function formatNewsDate(dateStr) {
  if (!dateStr) return '';
  try {
    const d = new Date(dateStr);
    return d.toLocaleDateString('en-GB', {day:'numeric',month:'short',hour:'2-digit',minute:'2-digit'});
  } catch { return dateStr.slice(0, 16); }
}

function escHtml(s) {
  return (s || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

// ══════════════════════════════════════════════════════════════════════════
// TOP MOVERS PAGE
// ══════════════════════════════════════════════════════════════════════════
async function loadMovers() {
  const container = document.getElementById('moversContainer');
  try {
    const data = await api('/movers');
    const gainers = data.gainers || [];
    const losers  = data.losers  || [];
    container.innerHTML = `
      <p class="movers-updated">Updated: ${data.updated || '—'}</p>
      <div class="movers-wrap">
        <div class="movers-section">
          <h3 class="gainers">🚀 Top 3 Gainers</h3>
          ${gainers.map(c => moverCardHtml(c, true)).join('')}
        </div>
        <div class="movers-section">
          <h3 class="losers">📉 Top 3 Losers</h3>
          ${losers.map(c => moverCardHtml(c, false)).join('')}
        </div>
      </div>`;
  } catch(e) {
    container.innerHTML = `<div class="err">⚠ Could not load movers data.<br>${e.message}</div>`;
  }
}

function moverCardHtml(c, isGainer) {
  const cls = isGainer ? 'up' : 'down';
  return `
    <div class="mover-card">
      <div class="mover-hdr">
        <div class="mover-info">
          <img class="mover-logo" src="${c.logo}" alt="${c.name}" onerror="this.style.display='none'"/>
          <div>
            <div class="mover-name">${escHtml(c.name)}</div>
            <div class="mover-sym">${c.symbol}/USD</div>
          </div>
        </div>
        <div class="mover-change ${cls}">${fmtPct(c.change_24h)}</div>
      </div>
      <div class="mover-price">${fmt(c.price)}</div>
      <div class="mover-why">💬 ${escHtml(c.explanation)}</div>
    </div>`;
}

// ══════════════════════════════════════════════════════════════════════════
// DASHBOARD
// ══════════════════════════════════════════════════════════════════════════
async function initDashboard() {
  buildSelector('coinSelector',   'bitcoin', 'selectHistCoin');
  buildSelector('msCoinSelector', 'bitcoin', 'selectMsCoin');
  buildCompareControls();
  await renderPrices();
  renderHistChart('bitcoin', '1825');
  renderCompare();
  renderMilestones('bitcoin');
  // Auto refresh every 15 seconds
  dashRefreshTimer = setInterval(() => refreshDashboard(), 15000);
}

async function refreshDashboard() {
  await renderPrices();
  document.getElementById('lastUpdated').textContent = new Date().toLocaleTimeString();
}

async function renderPrices() {
  const grid = document.getElementById('coinGrid');
  try {
    pricesData = await api('/prices');
    grid.innerHTML = '';
    for (const [id, d] of Object.entries(pricesData)) {
      const up = (d.change_24h || 0) >= 0;
      grid.innerHTML += `
        <div class="coin-card${id === selHistCoin ? ' active' : ''}" data-id="${id}" onclick="selectHistCoin('${id}')">
          <div class="coin-card-hdr">
            <div class="coin-info">
              <img class="coin-logo" src="${d.logo}" alt="${d.name}" onerror="this.style.display='none'"/>
              <div>
                <div class="coin-name">${d.name}</div>
                <div class="coin-sym">${d.symbol}/USD</div>
              </div>
            </div>
            <span class="badge ${up ? 'up' : 'down'}">${fmtPct(d.change_24h)}</span>
          </div>
          <div class="coin-price">${fmt(d.price)}</div>
          <div class="coin-stats">
            <div class="stat">
              <div class="stat-lbl">Market Cap</div>
              <div class="stat-val">${fmt(d.market_cap)}</div>
            </div>
            <div class="stat">
              <div class="stat-lbl">24h Change</div>
              <div class="stat-val ${pctCls(d.change_24h)}">${fmtPct(d.change_24h)}</div>
            </div>
          </div>
        </div>`;
    }
    updateTicker();
    document.getElementById('lastUpdated').textContent = new Date().toLocaleTimeString();
  } catch(e) {
    grid.innerHTML = `<div class="err">⚠ Cannot reach backend.<br><br>
      Make sure app.py is running:<br><strong>python app.py</strong><br><br>
      Then refresh this page.</div>`;
  }
}

function updateTicker() {
  const map = {bitcoin:'btc',ethereum:'eth',solana:'sol',binancecoin:'bnb',ripple:'xrp',cardano:'ada',dogecoin:'doge',avalanche:'avax'};
  for (const [id, d] of Object.entries(pricesData)) {
    const k = map[id]; if (!k) continue;
    ['', '2'].forEach(s => {
      const pe = document.getElementById(`t-${k}${s}`);
      const ce = document.getElementById(`t-${k}-c${s}`);
      if (pe) pe.textContent = fmt(d.price);
      if (ce) { ce.textContent = fmtPct(d.change_24h); ce.className = pctCls(d.change_24h); }
    });
  }
}

// ── History chart ──────────────────────────────────────────────────────────
function buildSelector(containerId, activeId, onClickFn) {
  document.getElementById(containerId).innerHTML =
    Object.entries(COINS_META).map(([id, m]) =>
      `<button class="sel-btn${id === activeId ? ' active' : ''}" data-id="${id}" onclick="${onClickFn}('${id}')">
        <img src="${m.logo}" alt="${m.name}" onerror="this.style.display='none'"/>${m.symbol}
      </button>`
    ).join('');
}

async function selectHistCoin(id) {
  selHistCoin = id;
  document.querySelectorAll('.coin-card').forEach(el => el.classList.toggle('active', el.dataset.id === id));
  document.querySelectorAll('#coinSelector .sel-btn').forEach(el => el.classList.toggle('active', el.dataset.id === id));
  renderHistChart(id, '1825');
  // Smooth scroll to chart
  document.getElementById('historyLabel').scrollIntoView({behavior:'smooth', block:'start'});
}

async function renderHistChart(coinId, days) {
  const panel = document.getElementById('historyPanel');
  panel.innerHTML = '<div class="loading"><div class="spin"></div>Loading data…</div>';
  try {
    const d = await api(`/history/${coinId}?days=${days}`);
    const meta  = COINS_META[coinId] || {};
    const color = d.color || meta.color || '#3bcefc';
    const ret   = d.total_return_pct;
    panel.innerHTML = `
      <div class="chart-hdr">
        <div class="coin-info" style="gap:12px">
          <img class="chart-coin-logo" src="${d.logo || meta.logo || ''}" alt="${d.name}" onerror="this.style.display='none'"/>
          <div>
            <div class="chart-coin-name">${d.name} <span style="color:var(--text3);font-size:13px;font-weight:400">(${d.symbol})</span></div>
            <div class="chart-coin-price">${fmt(d.last_price)}</div>
          </div>
        </div>
        <div>
          <div style="font-family:'Space Mono',monospace;font-size:11px;color:var(--text3);margin-bottom:3px">Return (period)</div>
          <div class="${pctCls(ret)}" style="font-family:'Space Mono',monospace;font-size:20px;font-weight:700">${fmtPct(ret)}</div>
        </div>
        <div class="period-tabs">
          ${[['90','3M'],['180','6M'],['365','1Y'],['730','2Y'],['1825','5Y']].map(([dv, lbl]) =>
            `<button class="period-btn${dv === days ? ' active' : ''}" onclick="renderHistChart('${coinId}','${dv}')">${lbl}</button>`
          ).join('')}
        </div>
      </div>
      <div class="chart-body">
        <div class="chart-container"><canvas id="histCanv"></canvas></div>
      </div>
      <div class="chart-stats-row">
        <div class="chart-stat"><div class="chart-stat-lbl">Period High</div><div class="chart-stat-val" style="color:var(--green)">${fmt(d.all_time_high)}</div></div>
        <div class="chart-stat"><div class="chart-stat-lbl">Period Low</div><div class="chart-stat-val" style="color:var(--red)">${fmt(d.all_time_low)}</div></div>
        <div class="chart-stat"><div class="chart-stat-lbl">Start Price</div><div class="chart-stat-val">${fmt(d.first_price)}</div></div>
        <div class="chart-stat"><div class="chart-stat-lbl">Total Return</div><div class="chart-stat-val ${pctCls(ret)}">${fmtPct(ret)}</div></div>
      </div>`;

    const ctx  = document.getElementById('histCanv').getContext('2d');
    if (histChart) histChart.destroy();
    const grad = ctx.createLinearGradient(0, 0, 0, 280);
    grad.addColorStop(0, color + '44');
    grad.addColorStop(1, color + '00');
    const step = Math.max(1, Math.floor(d.dates.length / 10));
    histChart = new Chart(ctx, {
      type:'line',
      data:{
        labels:d.dates,
        datasets:[{label:d.symbol,data:d.prices,borderColor:color,borderWidth:2,
          pointRadius:0,fill:true,backgroundColor:grad,tension:.3}]
      },
      options:{
        responsive:true,maintainAspectRatio:false,
        plugins:{
          legend:{display:false},
          tooltip:{
            backgroundColor:'#0f1a2e',borderColor:color+'55',borderWidth:1,
            callbacks:{label:c=>' '+fmt(c.parsed.y),title:c=>c[0].label}
          }
        },
        scales:{
          x:{ticks:{color:'#4d6b8a',font:{family:'Space Mono',size:10},maxRotation:0,
            callback(v,i){const dt=this.getLabelForValue(v);return dt&&i%step===0?dt.slice(0,7):''}},
            grid:{color:'rgba(99,189,255,.05)'}},
          y:{ticks:{color:'#4d6b8a',font:{family:'Space Mono',size:10},callback:v=>fmt(v)},
            grid:{color:'rgba(99,189,255,.05)'}}
        }
      }
    });
  } catch(e) {
    panel.innerHTML = `<div class="err">⚠ ${e.message}</div>`;
  }
}

// ── Compare ────────────────────────────────────────────────────────────────
function buildCompareControls() {
  const c = document.getElementById('compareControls');
  const periods = [['90','3M'],['180','6M'],['365','1Y'],['730','2Y'],['1825','5Y']];
  c.innerHTML = Object.entries(COINS_META).map(([id, m]) =>
    `<div class="cmp-toggle${cmpCoins.has(id) ? ' active' : ''}" onclick="toggleCmp('${id}')">
      <img src="${m.logo}" alt="${m.name}" onerror="this.style.display='none'"/>${m.symbol}
    </div>`
  ).join('') +
  `<div class="cmp-period">${periods.map(([dv, lbl]) =>
    `<button class="period-btn${dv === cmpPeriod ? ' active' : ''}" onclick="setCmpPeriod('${dv}',this)">${lbl}</button>`
  ).join('')}</div>`;
}

async function renderCompare() {
  const legend = document.getElementById('cmpLegend');
  legend.innerHTML = '<div class="loading"><div class="spin"></div>Loading comparison…</div>';
  const ctx = document.getElementById('cmpChart').getContext('2d');
  if (cmpChart) cmpChart.destroy();
  try {
    const d = await api(`/compare?coins=${[...cmpCoins].join(',')}&days=${cmpPeriod}`);
    const datasets = [];
    legend.innerHTML = '';
    for (const [id, cd] of Object.entries(d.coins)) {
      const color = cd.color || COINS_META[id]?.color || '#ffffff';
      datasets.push({label:cd.symbol,data:cd.normalized,borderColor:color,borderWidth:2,
        pointRadius:0,tension:.3,fill:false});
      const ret = cd.return_pct;
      legend.innerHTML += `
        <div class="legend-item">
          <div class="legend-dot" style="background:${color}"></div>
          <img src="${cd.logo||COINS_META[id]?.logo||''}" style="width:15px;height:15px;border-radius:50%" onerror="this.style.display='none'"/>
          <span class="legend-name">${cd.symbol}</span>
          <span class="legend-ret ${pctCls(ret)}">${fmtPct(ret)}</span>
        </div>`;
    }
    const step = Math.max(1, Math.floor((d.dates||[]).length / 10));
    cmpChart = new Chart(ctx, {
      type:'line',
      data:{labels:d.dates||[],datasets},
      options:{
        responsive:true,maintainAspectRatio:false,
        plugins:{
          legend:{display:false},
          tooltip:{backgroundColor:'#0f1a2e',borderColor:'rgba(99,189,255,.3)',borderWidth:1,
            callbacks:{label:c=>` ${c.dataset.label}: ${c.parsed.y.toFixed(1)} (indexed)`}}
        },
        scales:{
          x:{ticks:{color:'#4d6b8a',font:{family:'Space Mono',size:10},maxRotation:0,
            callback(v,i){const dt=this.getLabelForValue(v);return dt&&i%step===0?dt.slice(0,7):''}},
            grid:{color:'rgba(99,189,255,.05)'}},
          y:{ticks:{color:'#4d6b8a',font:{family:'Space Mono',size:10},callback:v=>v.toFixed(0)},
            grid:{color:'rgba(99,189,255,.05)'},
            title:{display:true,text:'Indexed (100 = start)',color:'#4d6b8a',font:{family:'Space Mono',size:10}}}
        }
      }
    });
  } catch(e) {
    legend.innerHTML = `<div class="err">⚠ ${e.message}</div>`;
  }
}

function toggleCmp(id) {
  if (cmpCoins.has(id)) {
    if (cmpCoins.size <= 2) return;
    cmpCoins.delete(id);
  } else {
    if (cmpCoins.size >= 5) cmpCoins.delete([...cmpCoins][0]);
    cmpCoins.add(id);
  }
  buildCompareControls();
  renderCompare();
}

function setCmpPeriod(d, btn) {
  cmpPeriod = d;
  document.querySelectorAll('.cmp-period .period-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  renderCompare();
}

// ── Milestones ─────────────────────────────────────────────────────────────
async function selectMsCoin(id) {
  selMsCoin = id;
  document.querySelectorAll('#msCoinSelector .sel-btn').forEach(el => el.classList.toggle('active', el.dataset.id === id));
  renderMilestones(id);
}

async function renderMilestones(coinId) {
  const panel = document.getElementById('milestonesPanel');
  panel.innerHTML = '<div class="loading"><div class="spin"></div>Loading milestones…</div>';
  try {
    const d = await api(`/milestones/${coinId}`);
    const maxAbs = Math.max(...(d.yearly_returns||[]).map(y => Math.abs(y.return_pct)), 1);
    panel.innerHTML = `
      <div class="ms-grid">
        <div class="ms-card"><div class="ms-icon">🏆</div><div class="ms-lbl">All-Time High (5yr)</div><div class="ms-val" style="color:var(--green)">${fmt(d.ath?.price)}</div><div class="ms-date">${d.ath?.date||'—'}</div></div>
        <div class="ms-card"><div class="ms-icon">📉</div><div class="ms-lbl">All-Time Low (5yr)</div><div class="ms-val" style="color:var(--red)">${fmt(d.atl?.price)}</div><div class="ms-date">${d.atl?.date||'—'}</div></div>
        <div class="ms-card"><div class="ms-icon">🚀</div><div class="ms-lbl">Best Single Day</div><div class="ms-val" style="color:var(--green)">+${(d.best_day?.change_pct||0).toFixed(2)}%</div><div class="ms-date">${d.best_day?.date||'—'} · ${fmt(d.best_day?.price)}</div></div>
        <div class="ms-card"><div class="ms-icon">💥</div><div class="ms-lbl">Worst Single Day</div><div class="ms-val" style="color:var(--red)">${(d.worst_day?.change_pct||0).toFixed(2)}%</div><div class="ms-date">${d.worst_day?.date||'—'} · ${fmt(d.worst_day?.price)}</div></div>
      </div>
      <div style="margin-top:28px">
        <div style="font-family:'Space Mono',monospace;font-size:11px;color:var(--text3);letter-spacing:.1em;text-transform:uppercase;margin-bottom:14px">
          Yearly Returns — ${d.symbol}
        </div>
        <div class="yearly-grid">
          ${(d.yearly_returns||[]).map(y => {
            const up = y.return_pct >= 0;
            const h  = Math.round((Math.abs(y.return_pct) / maxAbs) * 72);
            return `<div class="yr-wrap">
              <div class="yr-lbl">${y.year}</div>
              <div class="yr-bar-outer"><div class="yr-bar" style="height:${h}px;background:${up ? 'var(--green)' : 'var(--red)'}"></div></div>
              <div class="yr-pct ${up ? 'up' : 'down'}">${fmtPct(y.return_pct)}</div>
            </div>`;
          }).join('')}
        </div>
      </div>`;
  } catch(e) {
    panel.innerHTML = `<div class="err">⚠ ${e.message}</div>`;
  }
}

// ══════════════════════════════════════════════════════════════════════════
// LEARN PAGE
// ══════════════════════════════════════════════════════════════════════════
function toggleLesson(index) {
  const step   = document.querySelector(`.learn-step[data-step="${index}"]`);
  const body   = step.querySelector('.step-body');
  const toggle = step.querySelector('.step-toggle');
  const isOpen = body.classList.contains('open');
  // Close all
  document.querySelectorAll('.step-body').forEach(b => b.classList.remove('open'));
  document.querySelectorAll('.step-toggle').forEach(t => t.textContent = '+');
  // Open this one if it was closed
  if (!isOpen) {
    body.classList.add('open');
    toggle.textContent = '−';
  }
}

function completeLesson(index) {
  lessonsDone.add(index);
  localStorage.setItem('cipher_lessons', JSON.stringify([...lessonsDone]));
  const step = document.querySelector(`.learn-step[data-step="${index}"]`);
  if (step) step.classList.add('completed');
  const btn = step ? step.querySelector('.complete-btn') : null;
  if (btn) btn.textContent = '✓ Completed';
  renderLearnProgress();
}

function renderLearnProgress() {
  const total = 7;
  const done  = lessonsDone.size;
  const pct   = Math.round((done / total) * 100);
  const fill  = document.getElementById('learnProgressFill');
  const text  = document.getElementById('learnProgressText');
  const msg   = document.getElementById('learnCompleteMsg');
  if (fill) fill.style.width = pct + '%';
  if (text) text.textContent = `${done} of ${total} lessons completed`;
  if (msg)  msg.classList.toggle('show', done === total);
  // Mark completed steps
  lessonsDone.forEach(i => {
    const step = document.querySelector(`.learn-step[data-step="${i}"]`);
    if (step) {
      step.classList.add('completed');
      const btn = step.querySelector('.complete-btn');
      if (btn) btn.textContent = '✓ Completed';
    }
  });
}

// ══════════════════════════════════════════════════════════════════════════
// INIT
// ══════════════════════════════════════════════════════════════════════════
(function init() {
  // Restore theme
  const savedTheme = localStorage.getItem('cipher_theme') || 'dark';
  applyTheme(savedTheme);

  // Home page is shown by default (no lazy load needed)
  navigate('home');

  // Render learn progress on load (restores from localStorage)
  renderLearnProgress();
})();
