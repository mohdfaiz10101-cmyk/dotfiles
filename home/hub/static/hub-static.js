/* ── Hub 共享组件：侧边栏 + Cmd+K + WebSocket ── */
const HUB_NAV_GROUPS = [
  {
    icon: '🏠',
    label: '总览',
    items: [
      { href: '/',          icon: '🏠', label: '工作台' },
      { href: '/dashboard', icon: '📊', label: '系统全景' },
      { href: '/ai-panel',  icon: '🤖', label: 'AI 工作台' },
    ],
  },
  {
    icon: '📋',
    label: '任务协作',
    items: [
      { href: '/kanban', icon: '📋', label: '任务看板' },
      { href: '/ai-panel#tasks', icon: '📌', label: '任务中心' },
      { href: '/ai-panel#opencode-task', icon: '🚀', label: 'OP 待确认' },
    ],
  },
  {
    icon: '🛠',
    label: '服务与系统',
    items: [
      { href: '/control', icon: '🎛', label: '控制中心' },
      { href: '/ai-panel#diagnostics', icon: '🛠', label: '排查' },
    ],
  },
  {
    icon: '💬',
    label: '数据与业务',
    items: [
      { href: '/wechat', icon: '💬', label: '微信查询' },
      { href: '/search', icon: '🔍', label: '全局搜索' },
      { href: '/social-graph', icon: '🕸', label: '社交图谱' },
      { href: '/legacy-panel', icon: '🗂', label: '旧盘融合面板' },
    ],
  },
  {
    icon: '🎮',
    label: '设备与串流',
    items: [
      { href: '/ai-panel#moonlight', icon: '🎮', label: 'Moonlight 白名单' },
      { href: '/phone-health', icon: '📱', label: '手机健康' },
      { href: '/go/sunshine', icon: '☀️', label: 'Sunshine', external: false },
    ],
  },
  {
    icon: '⋯',
    label: '更多',
    items: [
      { href: '/ai-panel#mcp', icon: '📡', label: 'MCP 能力' },
      { href: '/ai-panel#n8n', icon: '⚡', label: 'n8n 状态' },
      { href: '/ai-panel#inbox', icon: '📬', label: '统一收件箱' },
    ],
  },
];

const HUB_NAV = HUB_NAV_GROUPS.flatMap(g => g.items);

/* ── 样式注入（一次性） ── */
function injectSidebarStyle() {
  if (document.getElementById('hub-sidebar-style')) return;
  const style = document.createElement('style');
  style.id = 'hub-sidebar-style';
  style.textContent = `
#hub-sidebar{
  position:fixed;left:0;top:0;height:100vh;width:236px;z-index:999;
  background:rgba(15,23,32,.95);border-right:1px solid rgba(255,255,255,.06);
  font-family:'Noto Sans CJK SC','Microsoft YaHei',sans-serif;
  backdrop-filter:blur(10px);transition:width .2s;overflow:hidden;
  display:flex;flex-direction:column;
}
#hub-sidebar.collapsed{width:44px;}
#hub-sidebar.collapsed .hub-sb-text,
#hub-sidebar.collapsed .hub-sb-title,
#hub-sidebar.collapsed .hub-sb-group-title,
#hub-sidebar.collapsed .hub-sb-group-text,
#hub-sidebar.collapsed .hub-sb-chevron,
#hub-sidebar.collapsed .hub-sb-foot{display:none;}
#hub-sidebar.collapsed .hub-sb-head{justify-content:center;padding:0 0 12px;}
#hub-sidebar.collapsed .hub-sb-link{display:none;}
#hub-sidebar.collapsed .hub-sb-logo{display:block;}
#hub-sidebar.collapsed .hub-sb-group-summary{justify-content:center;padding:11px 0;}
.hub-sb-head{display:flex;align-items:center;gap:8px;padding:14px 14px 12px;}
.hub-sb-logo{flex-shrink:0;filter:drop-shadow(0 0 6px rgba(116,211,154,.35));}
.hub-sb-title{font-size:15px;font-weight:700;color:#7db7ff;}
.hub-sb-toggle{margin-left:auto;background:none;border:none;color:#8da2b8;
  font-size:15px;cursor:pointer;padding:2px 4px;line-height:1;border-radius:4px;}
.hub-sb-toggle:hover{color:#e5eef8;background:rgba(255,255,255,.06);}
.hub-sb-nav{flex:1;display:flex;flex-direction:column;overflow-y:auto;padding-bottom:8px;}
.hub-sb-group{padding:6px 0;border-top:1px solid rgba(255,255,255,.045);}
.hub-sb-group:first-child{border-top:none;}
.hub-sb-group-summary{display:flex;align-items:center;gap:8px;padding:9px 14px;
  color:#e5eef8;cursor:pointer;user-select:none;font-size:13px;font-weight:700;
  list-style:none;border-left:3px solid transparent;}
.hub-sb-group-summary::-webkit-details-marker{display:none;}
.hub-sb-group-summary:hover{background:rgba(255,255,255,.04);border-left-color:#7db7ff;}
.hub-sb-group-icon{font-size:15px;flex-shrink:0;width:18px;text-align:center;}
.hub-sb-group-text{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}
.hub-sb-chevron{margin-left:auto;color:#667b90;font-size:10px;transition:transform .15s;}
.hub-sb-group[open] .hub-sb-chevron{transform:rotate(90deg);color:#7db7ff;}
.hub-sb-link{display:flex;align-items:center;gap:8px;padding:9px 14px;
  color:#8da2b8;text-decoration:none;font-size:13px;transition:.15s;
  border-left:3px solid transparent;white-space:nowrap;margin-left:10px;}
.hub-sb-link:hover{color:#e5eef8;background:rgba(255,255,255,.04);border-left-color:#7db7ff;}
.hub-sb-link.active{color:#7db7ff;background:rgba(125,183,255,.08);border-left-color:#7db7ff;}
.hub-sb-icon{font-size:14px;flex-shrink:0;width:18px;text-align:center;}
.hub-sb-text{overflow:hidden;text-overflow:ellipsis;}
.hub-sb-foot{margin-top:auto;padding:10px 14px;font-size:10px;color:#585b70;
  border-top:1px solid rgba(255,255,255,.04);}
.hub-sb-foot kbd{padding:1px 4px;border-radius:3px;background:rgba(255,255,255,.06);font-size:9px;}
.hub-sb-rail{position:fixed;left:0;top:0;height:100vh;width:8px;z-index:998;
  display:none;align-items:center;justify-content:center;cursor:pointer;}
.hub-sb-rail:hover{background:rgba(125,183,255,.08);}
.hub-sb-rail.show{display:flex;}
@media (max-width: 860px){
  #hub-sidebar{width:64px;touch-action:pan-y;}
  #hub-sidebar .hub-sb-text,
  #hub-sidebar .hub-sb-title,
  #hub-sidebar .hub-sb-group-text,
  #hub-sidebar .hub-sb-chevron,
  #hub-sidebar .hub-sb-foot{display:none;}
  #hub-sidebar .hub-sb-link{display:none;}
  #hub-sidebar .hub-sb-head{justify-content:center;padding:10px 0 8px;}
  #hub-sidebar .hub-sb-logo{display:block;}
  #hub-sidebar .hub-sb-toggle{margin-left:0;font-size:18px;}
  #hub-sidebar .hub-sb-group{padding:5px 0;}
  #hub-sidebar .hub-sb-group-summary{justify-content:center;padding:12px 0;border-left-width:3px;}
  #hub-sidebar .hub-sb-group-icon{width:30px;font-size:19px;}
  #hub-sidebar.mobile-open{width:min(84vw,320px);box-shadow:18px 0 60px rgba(0,0,0,.45);}
  #hub-sidebar.mobile-open .hub-sb-text,
  #hub-sidebar.mobile-open .hub-sb-title,
  #hub-sidebar.mobile-open .hub-sb-group-text,
  #hub-sidebar.mobile-open .hub-sb-chevron,
  #hub-sidebar.mobile-open .hub-sb-foot{display:block;}
  #hub-sidebar.mobile-open .hub-sb-link{display:flex;}
  #hub-sidebar.mobile-open .hub-sb-head{justify-content:flex-start;padding:14px 14px 12px;}
  #hub-sidebar.mobile-open .hub-sb-toggle{margin-left:auto;}
  #hub-sidebar.mobile-open .hub-sb-link{justify-content:flex-start;padding:10px 14px;}
  #hub-sidebar.mobile-open .hub-sb-icon{width:18px;font-size:14px;}
  #hub-sidebar.mobile-hidden{transform:translateX(-100%);}
  #hub-sidebar.mobile-hidden + #hub-sb-rail,
  #hub-sb-rail.show{display:flex;}
  .hub-sb-rail{width:18px;background:rgba(15,23,32,.4);}
}
`;
  document.head.appendChild(style);
}

/* ── 侧边栏 ── */
function injectSidebar() {
  if (document.getElementById('hub-sidebar')) return;
  injectSidebarStyle();
  const sb = document.createElement('nav');
  sb.id = 'hub-sidebar';
  sb.innerHTML = `
    <div class="hub-sb-head">
      <svg class="hub-sb-logo" width="20" height="20" viewBox="0 0 20 20" fill="none">
        <defs>
          <linearGradient id="hub-grad" x1="4" y1="4" x2="16" y2="16">
            <stop offset="0%" stop-color="#74d39a"/>
            <stop offset="100%" stop-color="#00d4aa"/>
          </linearGradient>
          <filter id="hub-glow">
            <feGaussianBlur stdDeviation="1.2" result="blur"/>
            <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
          </filter>
        </defs>
        <rect x="3" y="3" width="14" height="14" rx="4.5" fill="url(#hub-grad)" filter="url(#hub-glow)"/>
        <path d="M7 10.5L9 13L13 7.5" stroke="#0f1720" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
      </svg>
      <span class="hub-sb-title">Hub</span>
      <button class="hub-sb-toggle" title="收起 / 展开">◀</button>
    </div>
    <div class="hub-sb-nav">
      ${HUB_NAV_GROUPS.map(g => `
        <details class="hub-sb-group">
          <summary class="hub-sb-group-summary">
            <span class="hub-sb-group-icon">${g.icon}</span>
            <span class="hub-sb-group-text">${g.label}</span>
            <span class="hub-sb-chevron">›</span>
          </summary>
          ${g.items.map(n => `
            <a href="${n.href}" ${n.external ? 'target="_blank" rel="noreferrer"' : ''} class="hub-sb-link">
              <span class="hub-sb-icon">${n.icon}</span><span class="hub-sb-text">${n.label}</span>
            </a>`).join('')}
        </details>`).join('')}
    </div>
    <div class="hub-sb-foot"><kbd>⌘K</kbd> 快捷命令</div>`;
  document.body.prepend(sb);
  applySidebarLayout();
  bindSidebarGestures(sb);
  // 收起/展开（切换图标方向 + body margin + 显示 rail）
  sb.querySelector('.hub-sb-toggle').onclick = () => {
    if (isMobileHub()) {
      if (sb.classList.contains('mobile-open')) {
        closeMobileSidebar();
      } else {
        openMobileSidebar();
      }
      return;
    }
    sb.classList.add('collapsed');
    applySidebarLayout();
  };
}

function isMobileHub() {
  return window.matchMedia('(max-width: 860px)').matches;
}

function applySidebarLayout() {
  const sb = document.getElementById('hub-sidebar');
  if (!sb) return;
  const rail = document.getElementById('hub-sb-rail');
  if (isMobileHub()) {
    sb.classList.remove('collapsed');
    document.body.style.marginLeft = sb.classList.contains('mobile-hidden') ? '0' : '64px';
    sb.querySelector('.hub-sb-toggle').textContent = sb.classList.contains('mobile-open') ? '◀' : '▶';
    if (rail) rail.classList.toggle('show', sb.classList.contains('mobile-hidden'));
  } else if (sb.classList.contains('collapsed')) {
    sb.classList.remove('mobile-open', 'mobile-hidden');
    sb.querySelector('.hub-sb-toggle').textContent = '▶';
    document.body.style.marginLeft = '44px';
    if (rail) rail.classList.add('show');
  } else {
    sb.classList.remove('mobile-open');
    sb.classList.remove('mobile-hidden');
    sb.querySelector('.hub-sb-toggle').textContent = '◀';
    document.body.style.marginLeft = '236px';
    if (rail) rail.classList.remove('show');
  }
}

function openMobileSidebar() {
  const sb = document.getElementById('hub-sidebar');
  if (!sb) return;
  sb.classList.remove('mobile-hidden');
  sb.classList.add('mobile-open');
  applySidebarLayout();
}

function closeMobileSidebar() {
  const sb = document.getElementById('hub-sidebar');
  if (!sb) return;
  sb.classList.remove('mobile-open');
  sb.classList.add('mobile-hidden');
  applySidebarLayout();
}

function bindSidebarGestures(sb) {
  let startX = 0;
  let startY = 0;
  let tracking = false;
  let suppressClickUntil = 0;
  sb.addEventListener('click', (e) => {
    if (isMobileHub() && Date.now() < suppressClickUntil) {
      e.preventDefault();
      e.stopPropagation();
    }
  }, true);
  sb.addEventListener('touchstart', (e) => {
    if (!isMobileHub() || !e.touches.length) return;
    startX = e.touches[0].clientX;
    startY = e.touches[0].clientY;
    tracking = true;
  }, { passive: true });
  sb.addEventListener('touchend', (e) => {
    if (!tracking || !isMobileHub() || !e.changedTouches.length) return;
    tracking = false;
    const dx = e.changedTouches[0].clientX - startX;
    const dy = Math.abs(e.changedTouches[0].clientY - startY);
    if (dy > 60) return;
    if (Math.abs(dx) > 35) suppressClickUntil = Date.now() + 450;
    if (dx < -55) closeMobileSidebar();
    if (dx > 55) openMobileSidebar();
  }, { passive: true });
}

/* ── 收起后点边缘重新展开 ── */
function injectRail() {
  if (document.getElementById('hub-sb-rail')) return;
  const rail = document.createElement('div');
  rail.id = 'hub-sb-rail';
  rail.title = '展开侧边栏';
  document.body.appendChild(rail);
  rail.onclick = () => {
    const sb = document.getElementById('hub-sidebar');
    if (!sb) return;
    if (isMobileHub()) openMobileSidebar();
    else {
      sb.classList.remove('collapsed');
      applySidebarLayout();
    }
  };
  let startX = 0;
  rail.addEventListener('touchstart', (e) => {
    if (!e.touches.length) return;
    startX = e.touches[0].clientX;
  }, { passive: true });
  rail.addEventListener('touchend', (e) => {
    if (!e.changedTouches.length) return;
    if (e.changedTouches[0].clientX - startX > 35) openMobileSidebar();
  }, { passive: true });
}

function highlightNav() {
  const here = location.pathname + location.hash;
  let activeGroup = null;
  document.querySelectorAll('#hub-sidebar a').forEach(a => {
    const href = a.getAttribute('href') || '';
    const base = href.split('#')[0];
    const active = href === here || href === location.pathname || (base === location.pathname && !location.hash);
    a.classList.toggle('active', active);
    if (active) activeGroup = a.closest('.hub-sb-group');
  });
  const firstGroup = document.querySelector('#hub-sidebar .hub-sb-group');
  document.querySelectorAll('#hub-sidebar .hub-sb-group').forEach(group => {
    group.open = group === (activeGroup || firstGroup);
  });
}

/* ── Command Palette (⌘K / Ctrl+K) ── */
function injectCmdPalette() {
  if (document.getElementById('hub-cmd')) return;
  const overlay = document.createElement('div');
  overlay.id = 'hub-cmd';
  overlay.style.cssText = 'display:none;position:fixed;inset:0;background:rgba(0,0,0,.5);z-index:9999;justify-content:center;align-items:flex-start;padding-top:15vh;backdrop-filter:blur(2px)';
  overlay.innerHTML = `
    <div style="width:520px;max-width:90vw;background:#17212b;border:1px solid rgba(255,255,255,.08);border-radius:14px;
      box-shadow:0 20px 60px rgba(0,0,0,.4);overflow:hidden;font-family:'Noto Sans CJK SC','Microsoft YaHei',sans-serif">
      <input id="hub-cmd-input" type="text" placeholder="搜索页面 / 任务 / 服务…" autofocus
        style="width:100%;padding:14px 16px;background:transparent;border:none;border-bottom:1px solid rgba(255,255,255,.06);
        color:#e5eef8;font-size:15px;outline:none" />
      <div id="hub-cmd-results" style="max-height:320px;overflow-y:auto;padding:6px"></div>
    </div>`;
  document.body.appendChild(overlay);

  const input = overlay.querySelector('#hub-cmd-input');
  const results = overlay.querySelector('#hub-cmd-results');

  const CMD_ITEMS = [
    ...HUB_NAV.map(n => ({ type: 'page', label: `${n.icon} ${n.label}`, href: n.href, keywords: n.label })),
    { type: 'action', label: '🔄 刷新当前页', action: 'refresh', keywords: '刷新 reload' },
    { type: 'action', label: '📋 打开看板', action: 'kanban', href: '/kanban', keywords: '看板 kanban 任务' },
    { type: 'action', label: '🤖 打开 AI 工作台', action: 'ai-panel', href: '/ai-panel', keywords: 'ai panel agent' },
    { type: 'action', label: '🎛 打开控制中心', action: 'control', href: '/control', keywords: '控制中心 control 监控' },
  ];

  function render(items) {
    if (!items.length) { results.innerHTML = '<div style="padding:16px;color:#585b70;text-align:center;font-size:13px">无结果</div>'; return; }
    results.innerHTML = items.map(it => `
      <div class="hub-cmd-item" data-href="${it.href || ''}" data-action="${it.action || ''}"
        style="padding:10px 14px;cursor:pointer;font-size:13px;color:#cdd6f4;display:flex;align-items:center;gap:8px;border-radius:8px;margin:2px 4px"
        onmouseover="this.style.background='rgba(125,183,255,.08)'" onmouseout="this.style.background='transparent'">
        <span style="color:#8da2b8;font-size:11px;width:50px">${it.type === 'page' ? '页面' : '操作'}</span>
        <span>${it.label}</span>
      </div>
    `).join('');
    results.querySelectorAll('.hub-cmd-item').forEach(el => {
      el.addEventListener('click', () => {
        const href = el.dataset.href;
        const action = el.dataset.action;
        if (href) location.href = href;
        else if (action === 'refresh') location.reload();
        closeCmd();
      });
    });
  }

  function openCmd() {
    overlay.style.display = 'flex';
    input.value = '';
    input.focus();
    render(CMD_ITEMS);
  }
  function closeCmd() { overlay.style.display = 'none'; }

  overlay.addEventListener('click', e => { if (e.target === overlay) closeCmd(); });
  input.addEventListener('input', () => {
    const q = input.value.toLowerCase();
    render(CMD_ITEMS.filter(it => it.keywords && it.keywords.toLowerCase().includes(q)));
  });
  document.addEventListener('keydown', e => {
    if ((e.metaKey || e.ctrlKey) && e.key === 'k') { e.preventDefault(); openCmd(); }
    if (e.key === 'Escape') closeCmd();
  });
}

/* ── WebSocket 实时推送 ── */
function connectWS() {
  const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
  window.__hubWsRetries = window.__hubWsRetries || { status: 0, dialogue: 0 };
  
  // 系统状态推送
  const wsStatus = new WebSocket(`${proto}//${location.host}/ws/status`);
  wsStatus.onmessage = (ev) => {
    try {
      const msg = JSON.parse(ev.data);
      if (msg.type === 'status' && msg.data) {
        const data = msg.data;
        if (data.system) {
          window.dispatchEvent(new CustomEvent('hub:sys', { detail: data.system }));
        }
        if (data.services) {
          for (const svc of data.services) {
            window.dispatchEvent(new CustomEvent('hub:svc', { detail: { name: svc.name, status: svc.status } }));
          }
        }
        if (data.score) {
          window.dispatchEvent(new CustomEvent('hub:score', { detail: data.score }));
        }
      }
    } catch {}
  };
  wsStatus.onopen = () => { window.__hubWsRetries.status = 0; };
  wsStatus.onclose = () => {
    window.__hubWsRetries.status += 1;
    if (window.__hubWsRetries.status <= 3) setTimeout(connectWS, 5000);
  };
  
  // 对话推送（原有）
  const wsDialogue = new WebSocket(`${proto}//${location.host}/ws/dialogue`);
  wsDialogue.onmessage = (ev) => {
    try {
      const msg = JSON.parse(ev.data);
      window.dispatchEvent(new CustomEvent('hub:dialogue', { detail: msg }));
    } catch {}
  };
  wsDialogue.onopen = () => { window.__hubWsRetries.dialogue = 0; };
  wsDialogue.onclose = () => {
    window.__hubWsRetries.dialogue += 1;
    if (window.__hubWsRetries.dialogue <= 3) setTimeout(connectWS, 5000);
  };
}

function updateServiceDot(name, status) {
  // 由各页面自行实现，这里只发事件
  window.dispatchEvent(new CustomEvent('hub:svc', { detail: { name, status } }));
}
function pushAlert(msg) {
  window.dispatchEvent(new CustomEvent('hub:alert', { detail: msg }));
}

function shouldInjectSidebar() {
  return document.body?.dataset?.hubSidebar !== 'false';
}

/* ── 初始化 ── */
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    if (shouldInjectSidebar()) {
      injectSidebar();
      injectRail();
      highlightNav();
    }
    injectCmdPalette();
  });
} else {
  if (shouldInjectSidebar()) {
    injectSidebar();
    injectRail();
    highlightNav();
  }
  injectCmdPalette();
}
connectWS();
