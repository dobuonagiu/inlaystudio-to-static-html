/* ENGenius/IMPACT Static Site — Default app.js */
'use strict';

// ── Theme toggle ────────────────────────────────────
const THEME_KEY = 'site-theme';
function applyTheme(t) {
  document.documentElement.setAttribute('data-theme', t);
  localStorage.setItem(THEME_KEY, t);
  const btn = document.getElementById('theme-toggle');
  if (btn) { btn.textContent = t === 'dark' ? '☀️' : '🌙'; btn.title = t === 'dark' ? 'Tema chiaro' : 'Tema scuro'; }
  // Re-render tutti i diagrammi Mermaid col nuovo tema
  _reRenderAllMermaid(t);
}
(function initTheme() {
  const t = localStorage.getItem(THEME_KEY) || 'dark';
  document.documentElement.setAttribute('data-theme', t);
  document.addEventListener('DOMContentLoaded', function() {
    const btn = document.getElementById('theme-toggle');
    if (btn) {
      btn.textContent = t === 'dark' ? '☀️' : '🌙';
      btn.addEventListener('click', function() {
        const cur = document.documentElement.getAttribute('data-theme') || 'dark';
        applyTheme(cur === 'dark' ? 'light' : 'dark');
      });
    }
  });
})();

// ── Sidebar toggle ───────────────────────────────────
const SIDEBAR_KEY = 'site-sidebar';

function applySidebar(collapsed) {
  if (collapsed) {
    document.body.classList.add('sidebar-collapsed');
    localStorage.setItem(SIDEBAR_KEY, 'collapsed');
  } else {
    document.body.classList.remove('sidebar-collapsed');
    localStorage.setItem(SIDEBAR_KEY, 'open');
  }
  const btn = document.getElementById('sidebar-toggle');
  if (btn) { btn.textContent = collapsed ? '▶' : '◀'; btn.title = collapsed ? 'Apri menu' : 'Chiudi menu'; }
  // Aggiorna pan-zoom se ci sono diagrammi (cambio larghezza canvas)
  setTimeout(function() {
    Object.values(PZ).forEach(function(p) { try { p.resize(); p.fit(); p.center(); } catch(e) {} });
  }, 230);
}

(function initSidebar() {
  const collapsed = localStorage.getItem(SIDEBAR_KEY) === 'collapsed';
  applySidebar(collapsed);
  document.addEventListener('DOMContentLoaded', function() {
    const btn = document.getElementById('sidebar-toggle');
    if (btn) {
      btn.addEventListener('click', function() {
        applySidebar(!document.body.classList.contains('sidebar-collapsed'));
      });
    }
  });
})();

// ── Mermaid + Pan/Zoom ──────────────────────────────
const PZ = {};

function _pzInit(id, svgEl) {
  try {
    // Distruggi istanza precedente se esiste (re-render per cambio tema)
    if (PZ[id]) { try { PZ[id].destroy(); } catch(e) {} }
    PZ[id] = svgPanZoom(svgEl, {
      zoomEnabled: true,
      controlIconsEnabled: false,
      fit: true,
      center: true,
      minZoom: 0.05,
      maxZoom: 30,
      zoomScaleSensitivity: 0.3
    });
    PZ[id].resize();
    PZ[id].fit();
    PZ[id].center();
  } catch(e) { console.warn('svgPanZoom init error', id, e); }
}

// Renderizza un singolo .mermaid dal suo dataset.mermaidSrc
async function _renderOneDiagram(el) {
  const code = el.dataset.mermaidSrc;
  if (!code || !window.mermaid) return;
  const id = el.id;
  const tmpId = 'mmdr-' + id + '-' + Date.now();
  try {
    const { svg } = await mermaid.render(tmpId, code);
    el.innerHTML = svg;
    const svgEl = el.querySelector('svg');
    if (!svgEl || !window.svgPanZoom) return;
    const vb = svgEl.getAttribute('viewBox');
    let naturalW = parseFloat(svgEl.getAttribute('width') || '0');
    let naturalH = parseFloat(svgEl.getAttribute('height') || '0');
    if (vb) {
      const parts = vb.trim().split(/[\\s,]+/);
      if (parts.length === 4) {
        naturalW = naturalW || parseFloat(parts[2]);
        naturalH = naturalH || parseFloat(parts[3]);
      }
    }
    const canvas = el.closest('.mermaid-canvas');
    const cw = (canvas && canvas.offsetWidth) || 900;
    let idealH;
    if (naturalW > 0 && naturalH > 0) {
      const ratio = naturalH / naturalW;
      idealH = Math.round(cw * ratio);
      idealH = Math.max(300, Math.min(idealH, Math.round(window.innerHeight * 0.8)));
    } else {
      idealH = Math.max(420, Math.round(window.innerHeight * 0.55));
    }
    if (canvas) canvas.style.height = idealH + 'px';
    svgEl.removeAttribute('height'); svgEl.removeAttribute('width');
    svgEl.style.width = cw + 'px'; svgEl.style.height = idealH + 'px';
    svgEl.style.maxWidth = 'none'; svgEl.style.maxHeight = 'none';
    svgEl.style.display = 'block';
    setTimeout(function() { _pzInit(id, svgEl); }, 100);
  } catch(e) {
    el.innerHTML = '<div style="padding:2rem;color:#ef4444;font-family:monospace;font-size:.85rem">Errore rendering: ' + (e.message||e) + '</div>';
  }
}

// Re-render tutti i diagrammi con il nuovo tema
async function _reRenderAllMermaid(theme) {
  if (!window.mermaid) return;
  mermaid.initialize({
    startOnLoad: false,
    theme: theme === 'light' ? 'default' : 'dark',
    securityLevel: 'loose',
    flowchart: { useMaxWidth: false },
    sequence: { useMaxWidth: false },
    er: { useMaxWidth: false },
  });
  const diagrams = document.querySelectorAll('.mermaid-canvas .mermaid');
  for (const el of diagrams) {
    if (el.dataset.mermaidSrc) { await _renderOneDiagram(el); }
  }
}

async function initMermaid() {
  if (!window.mermaid) return;
  const theme = localStorage.getItem(THEME_KEY) === 'light' ? 'default' : 'dark';
  mermaid.initialize({
    startOnLoad: false,
    theme: theme,
    securityLevel: 'loose',
    flowchart: { useMaxWidth: false },
    sequence: { useMaxWidth: false },
    er: { useMaxWidth: false },
  });
  const diagrams = document.querySelectorAll('.mermaid-canvas .mermaid');
  for (const el of diagrams) {
    const id = el.id || ('mmd-' + Math.random().toString(36).substr(2,8));
    el.id = id;
    const code = el.textContent.trim();
    if (!code) continue;
    // Salva il sorgente PRIMA del render (dopo innerHTML viene perso)
    el.dataset.mermaidSrc = code;
    await _renderOneDiagram(el);
  }
}

document.addEventListener('DOMContentLoaded', initMermaid);

function pzIn(id)    { if (PZ[id]) PZ[id].zoomIn(); }
function pzOut(id)   { if (PZ[id]) PZ[id].zoomOut(); }
function pzReset(id) { if (PZ[id]) { PZ[id].resize(); PZ[id].fit(); PZ[id].center(); } }
function pzFull(id)  {
  const canvas = document.getElementById(id + '-canvas');
  if (!canvas) return;
  if (!document.fullscreenElement) canvas.requestFullscreen().catch(function(){});
  else document.exitFullscreen();
}
function pzSvg(id) {
  const svg = document.querySelector('#' + id + ' svg');
  if (!svg) return;
  const blob = new Blob([svg.outerHTML], {type:'image/svg+xml;charset=utf-8'});
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a'); a.href = url; a.download = id + '.svg';
  document.body.appendChild(a); a.click(); document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

// Aggiorna dimensioni SVG e pan-zoom dopo resize finestra o fullscreen
function _pzRefreshAll() {
  document.querySelectorAll('.mermaid-canvas .mermaid').forEach(function(el) {
    const canvas = el.closest('.mermaid-canvas');
    const svgEl = el.querySelector('svg');
    if (canvas && svgEl) {
      const cw = canvas.offsetWidth;
      const ch = canvas.offsetHeight;
      if (cw > 0 && ch > 0) {
        svgEl.style.width = cw + 'px';
        svgEl.style.height = ch + 'px';
      }
    }
  });
  setTimeout(function() {
    Object.values(PZ).forEach(function(p) {
      try { p.resize(); p.fit(); p.center(); } catch(e) {}
    });
  }, 50);
}

window.addEventListener('resize', function() {
  clearTimeout(window._pzResizeTimer);
  window._pzResizeTimer = setTimeout(_pzRefreshAll, 200);
});

document.addEventListener('fullscreenchange', function() {
  setTimeout(_pzRefreshAll, 250);
});

// ── Search ──────────────────────────────────────────
let lunrIdx = null, searchDocs = [];

function initSearchIndex(docs) {
  searchDocs = docs;
  if (!window.lunr) return;
  lunrIdx = lunr(function() {
    this.ref('id');
    this.field('title',   { boost: 10 });
    this.field('project', { boost: 5  });
    this.field('category',{ boost: 3  });
    this.field('content');
    docs.forEach(d => this.add(d));
  });
}

function pntSearch(query, limit) {
  if (!lunrIdx || !query.trim()) return [];
  limit = limit || 10;
  try {
    const terms = query.trim().split(/\\s+/);
    const q = terms.map((t,i) => i === terms.length-1 ? t+'* '+t+'~1' : t+'~1').join(' ');
    return lunrIdx.search(q).slice(0, limit).map(r => ({...searchDocs.find(d=>d.id===r.ref), score:r.score}));
  } catch(e) { return []; }
}

function snippet(content, query, len) {
  len = len || 160;
  const words = query.trim().split(/\\s+/).filter(Boolean);
  const re = new RegExp(words.map(w=>w.replace(/[.*+?^${}()|[\\]\\\\]/g,'\\\\')).join('|'),'i');
  const idx = content.search(re);
  const start = Math.max(0, idx-50);
  let raw = content.slice(start, start+len);
  words.forEach(w => {
    raw = raw.replace(new RegExp('('+w.replace(/[.*+?^${}()|[\\]\\\\]/g,'\\\\')+')', 'gi'), '<mark>$1</mark>');
  });
  return (start > 0 ? '…' : '') + raw + (start+len < content.length ? '…' : '');
}

const CAT_COLORS = {
  'Main':'#1e40af:#dbeafe','Enterprise':'#6d28d9:#ede9fe',
  'Artefatto':'#047857:#d1fae5','Processo':'#b45309:#fef3c7',
  'Deep Dive':'#b91c1c:#fee2e2','Test Spec':'#0e7490:#cffafe',
  'Use Case':'#7c3aed:#ede9fe','Requisiti':'#854d0e:#fef3c7',
  'Default':'#475569:#f1f5f9'
};
function catBadgeHtml(cat) {
  const [bg, color] = (CAT_COLORS[cat]||CAT_COLORS.Default).split(':');
  return `<span class="sr-badge" style="background:${color};color:${bg}">${cat}</span>`;
}

// Full search page
function doSearchPage(q) {
  const container = document.getElementById('search-results');
  if (!container) return;
  if (!q) { container.innerHTML = '<p style="color:var(--c-muted)">Digita una parola chiave.</p>'; return; }
  const results = pntSearch(q, 30);
  if (!results.length) {
    container.innerHTML = '<p>Nessun risultato per <strong>' + q + '</strong>.</p>'; return;
  }
  container.innerHTML = '<p style="color:var(--c-muted);margin-bottom:1rem">' + results.length + ' risultati per <strong>' + q + '</strong></p>' +
    results.map(d => `<div class="sr-card">
      <div>${catBadgeHtml(d.category||'Default')}<a href="${d.url}">${d.title}</a></div>
      <div class="sr-snippet">${snippet(d.content||'', q)}</div>
      <div class="sr-meta">${d.project||''} &bull; ${d.url||''}</div>
    </div>`).join('');
}

document.addEventListener('DOMContentLoaded', function() {
  // init search from global index
  if (window.SITE_SEARCH_INDEX && window.lunr) {
    lunr.load ? lunr.load(window.SITE_SEARCH_INDEX) : null;
    initSearchIndex(window.SITE_SEARCH_INDEX);
  }
  // search page
  const si = document.getElementById('search-input');
  const sr = document.getElementById('search-results');
  if (si && sr) {
    const urlQ = new URLSearchParams(window.location.search).get('q') || '';
    if (urlQ) { si.value = urlQ; doSearchPage(urlQ); }
    si.addEventListener('input', function() {
      clearTimeout(si._t);
      si._t = setTimeout(() => doSearchPage(si.value.trim()), 250);
    });
    si.addEventListener('keydown', function(e) {
      if (e.key === 'Enter') {
        history.replaceState({},'','?q='+encodeURIComponent(si.value));
        doSearchPage(si.value.trim());
      }
    });
  }
  // search category buttons
  document.querySelectorAll('.cat-btn').forEach(btn => {
    btn.addEventListener('click', function() {
      const term = this.dataset.term;
      if (si) { si.value = term; doSearchPage(term); }
    });
  });
});
