#!/usr/bin/env python3
"""
ENGenius/IMPACT Static Site Generator
======================================
Genera un sito HTML statico dai documenti prodotti da ENGenius e IMPACT.

Uso:
    python3 generate_site.py                           # cerca site_config.yaml nel CWD
    python3 generate_site.py --config path/to/config.yaml
    python3 generate_site.py --css path/to/custom.css  # CSS custom (override config)
    python3 generate_site.py --project <id>            # rigenera solo un progetto

Output:
    Directory configurata in site_config.yaml (default: ./docs/)
"""

import os, re, json, shutil, sys, argparse
from pathlib import Path
from datetime import datetime
from html import escape as h

try:
    import yaml
except ImportError:
    print("❌  Errore: modulo 'pyyaml' non trovato. Installa con: pip install pyyaml")
    sys.exit(1)

_SCRIPT_DIR     = Path(__file__).parent
_DEFAULT_ASSETS = _SCRIPT_DIR / 'assets'

# ═══════════════════════════════════════════════════════════
#  CLI ARGS + CONFIG LOADING
# ═══════════════════════════════════════════════════════════

def _parse_args():
    ap = argparse.ArgumentParser(
        description='ENGenius/IMPACT Static Site Generator',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument('--config', default='site_config.yaml',
                    help='Path al file site_config.yaml (default: site_config.yaml nel CWD)')
    ap.add_argument('--css', default=None, metavar='PATH',
                    help='CSS custom — sovrascrive css_file dal config')
    ap.add_argument('--js',  default=None, metavar='PATH',
                    help='JS custom — sovrascrive js_file dal config')
    ap.add_argument('--project', default=None, metavar='ID',
                    help='Rigenera solo il progetto con questo ID (build incrementale)')
    return ap.parse_args()

def _load_config(config_path: Path) -> dict:
    with open(config_path, 'r', encoding='utf-8') as f:
        cfg = yaml.safe_load(f)
    return cfg or {}

def _resolve_path(raw, config_dir: Path) -> Path:
    p = Path(raw)
    return p if p.is_absolute() else (config_dir / p).resolve()

def _build_repos(projects: list, config_dir: Path) -> list:
    """Build the REPOS list from config, resolving paths relative to the config file."""
    repos = []
    for p in projects:
        path = _resolve_path(p['path'], config_dir)
        def _opt(key):
            v = p.get(key)
            return _resolve_path(v, config_dir) if v else None
        repos.append({
            'id':               p['id'],
            'name':             p.get('name', p['id']),
            'label':            p.get('label', p['id']),
            'short':            p.get('short', p['id'][:3].upper()),
            'path':             path,
            'type':             p.get('type', 'backend'),
            'color':            p.get('color', 'backend'),
            'badge':            p.get('badge', p.get('type', 'Service').capitalize()),
            'desc':             p.get('desc', ''),
            'stack':            p.get('stack', []),
            'docs_path':        _opt('docs_path'),
            'artifacts_path':   _opt('artifacts_path'),
            'enterprise_path':  _opt('enterprise_path'),
            'docmind_project':  p.get('docmind_project'),
        })
    return repos

def _load_asset(filename: str, override: str = None, config_override: str = None) -> str:
    """Load CSS or JS from: CLI override > config override > default assets."""
    for src in [override, config_override]:
        if src:
            p = Path(src)
            if not p.is_absolute():
                p = Path.cwd() / p
            if p.exists():
                return p.read_text(encoding='utf-8')
            print(f'  ⚠️  Asset non trovato: {p}, uso default')
    p = _DEFAULT_ASSETS / filename
    if p.exists():
        return p.read_text(encoding='utf-8')
    raise FileNotFoundError(f'Asset di default non trovato: {p}  —  Reinstalla la skill.')

DOC_LABELS = {
    '00_deep_dive': ('Deep Dive', '🔬'),
    '01_context': ('Contesto', '📋'),
    '02_functional_overview': ('Funzionale', '⚙️'),
    '03_non_functional_overview': ('Non-Funzionale', '📐'),
    '04_constraints': ('Vincoli', '🔒'),
    '05_principles': ('Principi', '📌'),
    '06_software_architecture': ('Architettura SW', '🏗️'),
    '07_code': ('Codice', '💻'),
    '08_data': ('Dati / MongoDB', '🗄️'),
    '09_infrastructure_architecture': ('Infrastruttura', '☁️'),
    '10_deployment': ('Deployment', '🚀'),
    '11_development_environment': ('Dev Environment', '🛠️'),
    '12_operation_and_support': ('Operativo', '🔧'),
    '13_decision_log': ('Decision Log', '📝'),
    '14_metrics': ('Metriche', '📊'),
    '15_fp_cocomo': ('FP/COCOMO', '📈'),
    '16_frontend_deep_assessment': ('Frontend Assessment', '🖥️'),
    '17_backend_deep_assessment': ('Backend Assessment', '⚡'),
    '18_antipattern_deep_dive': ('Antipattern', '⚠️'),
    '19_modernization_estimation_spec': ('Modernization', '🔄'),
}

ENT_LABELS = {
    '00_portfolio_overview': ('Portfolio Overview', '📊'),
    '01_tech_stack_matrix': ('Tech Stack Matrix', '⚙️'),
    '02_system_landscape': ('System Landscape', '🌐'),
    '03_risk_heatmap': ('Risk Heatmap', '⚠️'),
    '04_decisions_rollup': ('Decisions Roll-up', '📝'),
    '05_portfolio_sizing': ('Portfolio Sizing', '📏'),
    '06_modernization_roadmap': ('Modernization Roadmap', '🗺️'),
}

# ENGenius forward-engineering artifacts (artifacts/*.md)
# Ramo standard ANALYSIS: 01_business_requirements, 02_functional_requirements, ...
# Ramo agile ANALYSIS (02b): 01_ba, 02_epics, 04_user_stories
ARTIFACT_LABELS = {
    # ── Standard ANALYSIS ────────────────────────────
    '01_business_requirements':        ('Business Requirements', '📋'),
    '02_functional_requirements':      ('Functional Requirements', '⚙️'),
    '03_features':                     ('Features', '✨'),
    '04_use_cases':                    ('Use Cases', '👤'),
    '04b_scenarios':                   ('Scenarios', '🎭'),
    '04c_non_functional_requirements': ('Non-Functional Requirements', '📐'),
    '04-fp-sizing':                    ('FP Sizing', '📏'),
    '05_logical_entities':             ('Logical Entities', '🗂️'),
    '06_processes':                    ('Processes', '↔️'),
    '07_components':                   ('Components', '🧩'),
    '08_dependencies':                 ('Dependencies', '🔗'),
    '09_architecture_design':          ('Architecture Design', '🏗️'),
    '09_specs_catalog':                ('Specs Catalog', '📑'),
    '10_coverage_matrix':              ('Coverage Matrix', '✅'),
    '11_cost_matrix':                  ('Cost Matrix', '💰'),
    # ── Agile ANALYSIS (02b_agile_analysis) ──────────
    '01_ba':           ('Business Analysis', '🧠'),
    '02_epics':        ('Epics', '📊'),
    '04_user_stories': ('User Stories', '👤'),
}

# ENGenius test spec artifacts (artifacts/test_spec/*.md)
TEST_SPEC_LABELS = {
    '01-test-units':     ('Test Units', '🔬'),
    '02-test-rules':     ('Test Rules', '📏'),
    '03-test-scenarios': ('Test Scenarios', '🎭'),
    '04-test-cases':     ('Test Cases', '🧪'),
}

GEN_DATE = datetime.now().strftime('%Y-%m-%d')
_mermaid_seq = 0

def _next_mmd():
    global _mermaid_seq
    _mermaid_seq += 1
    return f'mmd{_mermaid_seq}'

# ═══════════════════════════════════════════════════════════
#  MARKDOWN → HTML
# ═══════════════════════════════════════════════════════════

def process_inline(text):
    """Convert inline markdown to HTML (bold, italic, code, links)."""
    # store inline code with placeholder to avoid escaping its content
    codes = {}
    cc = [0]
    def _store_code(m):
        k = f'ICODE{cc[0]}X'
        cc[0] += 1
        codes[k] = f'<code>{h(m.group(1))}</code>'
        return k
    text = re.sub(r'`(.+?)`', _store_code, text)
    # escape html in non-code text
    text = h(text)
    # bold + italic
    text = re.sub(r'\*\*\*(.+?)\*\*\*', r'<strong><em>\1</em></strong>', text)
    # bold
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    # italic
    text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)
    # strikethrough
    text = re.sub(r'~~(.+?)~~', r'<del>\1</del>', text)
    # links
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', text)
    # restore code
    for k, v in codes.items():
        text = text.replace(h(k), v)
    return text

def _make_table(lines):
    """Convert markdown table lines to HTML."""
    rows = []
    for ln in lines:
        cells = [c.strip() for c in ln.strip().strip('|').split('|')]
        rows.append(cells)
    if len(rows) < 2:
        return ''
    header = rows[0]
    # skip separator row (row 1)
    body = rows[2:] if len(rows) > 2 else []
    th = ''.join(f'<th>{process_inline(c)}</th>' for c in header)
    trs = ''
    for row in body:
        # pad or trim to header length
        while len(row) < len(header):
            row.append('')
        tds = ''.join(f'<td>{process_inline(row[i])}</td>' for i in range(len(header)))
        trs += f'<tr>{tds}</tr>'
    return f'<div class="table-wrap"><table><thead><tr>{th}</tr></thead><tbody>{trs}</tbody></table></div>'

def _make_mermaid(code):
    uid = _next_mmd()
    # Wrap path-like node labels in quotes to fix Mermaid lexical errors
    # e.g. CFG[/opt/pnt/config] → CFG["/opt/pnt/config"]
    code = re.sub(r'\[(/[^\]"]+)\]', r'["\1"]', code)
    escaped = h(code.strip())
    return f'''<div class="mermaid-wrap" id="{uid}-wrap">
  <div class="mermaid-toolbar">
    <div class="diag-title-area">
      <h1>Diagramma</h1>
      <p class="diag-desc">Scroll per zoom &bull; Drag per navigare</p>
    </div>
    <button class="toolbar-btn" title="Zoom +" onclick="pzIn('{uid}')">🔍 Zoom +</button>
    <button class="toolbar-btn" title="Zoom −" onclick="pzOut('{uid}')">🔍 Zoom −</button>
    <button class="toolbar-btn" title="Reset" onclick="pzReset('{uid}')">↺ Reset</button>
    <button class="toolbar-btn" title="Fullscreen" onclick="pzFull('{uid}')">⛶ Fullscreen</button>
    <button class="toolbar-btn toolbar-btn-primary" title="Scarica SVG" onclick="pzSvg('{uid}')">⬇ SVG</button>
  </div>
  <div class="mermaid-canvas" id="{uid}-canvas">
    <div class="mermaid" id="{uid}">{escaped}</div>
    <div class="zoom-hint">Scroll: zoom &bull; Drag: pan</div>
  </div>
</div>'''

def md_to_html(text):
    """Convert full markdown document to HTML."""
    lines = text.split('\n')
    out = []
    i = 0
    while i < len(lines):
        ln = lines[i]

        # fenced code block
        if ln.startswith('```') or ln.startswith('~~~'):
            fence = ln[:3]
            lang = ln[3:].strip().lower()
            code_lines = []
            i += 1
            while i < len(lines) and not lines[i].startswith(fence):
                code_lines.append(lines[i])
                i += 1
            i += 1  # skip closing fence
            code = '\n'.join(code_lines)
            if lang == 'mermaid':
                out.append(_make_mermaid(code))
            else:
                lc = f' class="language-{lang}"' if lang else ''
                out.append(f'<pre><code{lc}>{h(code)}</code></pre>')
            continue

        # ATX heading
        m = re.match(r'^(#{1,6})\s+(.*)', ln)
        if m:
            lvl = len(m.group(1))
            txt = m.group(2).rstrip('#').strip()
            slug = re.sub(r'[^\w\s-]', '', txt.lower()).strip()
            slug = re.sub(r'\s+', '-', slug)
            out.append(f'<h{lvl} id="{slug}">{process_inline(txt)}</h{lvl}>')
            i += 1
            continue

        # horizontal rule
        if re.match(r'^(\-{3,}|\*{3,}|={3,})\s*$', ln):
            out.append('<hr>')
            i += 1
            continue

        # table (lines starting and ending with |)
        if ln.strip().startswith('|') and '|' in ln[1:]:
            tbl_lines = []
            while i < len(lines) and lines[i].strip().startswith('|') and '|' in lines[i][1:]:
                tbl_lines.append(lines[i])
                i += 1
            if len(tbl_lines) >= 2:
                out.append(_make_table(tbl_lines))
            continue

        # blockquote
        if ln.startswith('>'):
            bq_lines = []
            while i < len(lines) and lines[i].startswith('>'):
                bq_lines.append(lines[i][1:].lstrip(' '))
                i += 1
            inner = md_to_html('\n'.join(bq_lines))
            out.append(f'<blockquote>{inner}</blockquote>')
            continue

        # unordered list
        if re.match(r'^(\s*)[-*+]\s', ln):
            indent0 = len(ln) - len(ln.lstrip())
            items_html = []
            while i < len(lines):
                ll = lines[i]
                if not ll.strip():
                    i += 1
                    break
                mm = re.match(r'^(\s*)[-*+]\s+(.*)', ll)
                if mm:
                    items_html.append(f'<li>{process_inline(mm.group(2))}</li>')
                    i += 1
                else:
                    break
            out.append('<ul>' + ''.join(items_html) + '</ul>')
            continue

        # ordered list
        if re.match(r'^\s*\d+\.\s', ln):
            items_html = []
            while i < len(lines):
                ll = lines[i]
                if not ll.strip():
                    i += 1
                    break
                mm = re.match(r'^\s*\d+\.\s+(.*)', ll)
                if mm:
                    items_html.append(f'<li>{process_inline(mm.group(1))}</li>')
                    i += 1
                else:
                    break
            out.append('<ol>' + ''.join(items_html) + '</ol>')
            continue

        # empty line
        if not ln.strip():
            i += 1
            continue

        # paragraph — collect until structural break
        para_lines = []
        while i < len(lines):
            ll = lines[i]
            if (not ll.strip()
                or ll.startswith('#')
                or ll.startswith('>')
                or ll.startswith('```')
                or ll.startswith('~~~')
                or re.match(r'^(\-{3,}|\*{3,}|={3,})\s*$', ll)
                or re.match(r'^(\s*)[-*+]\s', ll)
                or re.match(r'^\s*\d+\.\s', ll)
                or (ll.strip().startswith('|') and '|' in ll[1:])):
                break
            para_lines.append(ll)
            i += 1
        if para_lines:
            out.append(f'<p>{process_inline(" ".join(para_lines))}</p>')

    return '\n'.join(out)

def md_bold(text):
    """Converti **testo** → <strong>testo</strong> dopo html-escape."""
    return re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', h(text))

# ═══════════════════════════════════════════════════════════
#  DOC SCANNER
# ═══════════════════════════════════════════════════════════

def extract_title(md_text):
    for ln in md_text.split('\n'):
        m = re.match(r'^#\s+(.*)', ln)
        if m:
            return m.group(1).strip()
    return ''

def extract_summary(md_text, chars=600):
    """Extract first paragraph/summary block."""
    lines = md_text.split('\n')
    collecting = False
    buf = []
    for ln in lines:
        if re.match(r'^##?\s+', ln) and not collecting:
            collecting = True
            continue
        if collecting:
            if not ln.strip():
                if buf:
                    break
                continue
            if ln.startswith('#'):
                break
            if ln.startswith('|') or ln.startswith('```'):
                break
            buf.append(ln.strip())
    text = ' '.join(buf)
    if len(text) > chars:
        text = text[:chars] + '…'
    return text

def scan_docs(repo):
    """Return list of doc dicts for a repo, discovering all doc types dynamically."""
    docs = []
    project_path = repo['path']
    is_parent = repo.get('type') == 'parent'

    if is_parent:
        # ── Enterprise docs: _enterprise/ or documentazione/enterprise/ ──
        ent_path = repo.get('enterprise_path')
        if ent_path is None:
            ent_path = project_path / '_enterprise'
            if not ent_path.exists():
                ent_path = project_path / 'documentazione' / 'enterprise'
        if ent_path and ent_path.exists():
            for p in sorted(ent_path.glob('*.md')):
                stem = p.stem
                label, icon = ENT_LABELS.get(stem, (stem.replace('_', ' ').title(), '📄'))
                text = p.read_text(encoding='utf-8', errors='replace')
                docs.append({
                    'repo_id': repo['id'],
                    'path': p,
                    'stem': stem,
                    'category': 'enterprise',
                    'label': label,
                    'icon': icon,
                    'title': extract_title(text) or label,
                    'summary': extract_summary(text),
                    'url': f'enterprise/{stem}.html',
                    'text': text,
                })

        # ── Requirement coverage docs (legacy path) ──
        req_path = project_path / 'documentazione' / 'requirement_coverage'
        if req_path.exists():
            for p in sorted(req_path.glob('*.md')):
                stem = p.stem
                text = p.read_text(encoding='utf-8', errors='replace')
                label = stem.replace('_', ' ').title()
                docs.append({
                    'repo_id': repo['id'],
                    'path': p,
                    'stem': stem,
                    'category': 'requirement_coverage',
                    'label': label,
                    'icon': '📋',
                    'title': extract_title(text) or label,
                    'summary': extract_summary(text),
                    'url': f'requirements/{stem}.html',
                    'text': text,
                })

    else:
        # ── IMPACT how: docs/*.md ────────────────────────────────────────────
        docs_path = repo.get('docs_path') or (project_path / 'docs')
        if docs_path and docs_path.exists():
            for p in sorted(docs_path.glob('*.md')):
                stem = p.stem
                label, icon = DOC_LABELS.get(stem, (stem.replace('_', ' ').title(), '📄'))
                text = p.read_text(encoding='utf-8', errors='replace')
                docs.append({
                    'repo_id': repo['id'],
                    'path': p,
                    'stem': stem,
                    'category': 'main',
                    'label': label,
                    'icon': icon,
                    'title': extract_title(text) or label,
                    'summary': extract_summary(text),
                    'url': f'projects/{repo["id"]}/{stem}.html',
                    'text': text,
                })

            # ── IMPACT what-process: docs/impact/how/processes/*.md ──────────
            proc_path = docs_path / 'impact' / 'how' / 'processes'
            if proc_path.exists():
                for p in sorted(proc_path.glob('*.md')):
                    stem = p.stem
                    text = p.read_text(encoding='utf-8', errors='replace')
                    label = stem.replace('process_', '').replace('_', ' ').title()
                    ep_m = re.search(r'\*\*Entry Point\*\*\s*\|\s*[`"]?([^`"\|\n]+)[`"]?', text)
                    entry_point = ep_m.group(1).strip().strip('`') if ep_m else ''
                    docs.append({
                        'repo_id': repo['id'],
                        'path': p,
                        'stem': stem,
                        'category': 'process',
                        'label': label,
                        'icon': '↔️',
                        'title': extract_title(text) or label,
                        'summary': extract_summary(text),
                        'entry_point': entry_point,
                        'url': f'projects/{repo["id"]}/impact/process/{stem}.html',
                        'text': text,
                    })

            # ── IMPACT how-deepdive: docs/impact/how/deepdive/*.md ───────────
            dd_path = docs_path / 'impact' / 'how' / 'deepdive'
            if dd_path.exists():
                for p in sorted(dd_path.glob('*.md')):
                    stem = p.stem
                    text = p.read_text(encoding='utf-8', errors='replace')
                    label = stem.replace('deepdive_', '').replace('_', ' ').title()
                    docs.append({
                        'repo_id': repo['id'],
                        'path': p,
                        'stem': stem,
                        'category': 'deepdive',
                        'label': label,
                        'icon': '🔎',
                        'title': extract_title(text) or label,
                        'summary': extract_summary(text),
                        'url': f'projects/{repo["id"]}/impact/deepdive/{stem}.html',
                        'text': text,
                    })

            # ── IMPACT what: docs/impact/what/*.md ───────────────────────────
            what_path = docs_path / 'impact' / 'what'
            if what_path.exists():
                for p in sorted(what_path.glob('*.md')):
                    stem = p.stem
                    text = p.read_text(encoding='utf-8', errors='replace')
                    label = stem.replace('USE_CASE_', '').replace('use_case_', '').replace('_', ' ').title()
                    docs.append({
                        'repo_id': repo['id'],
                        'path': p,
                        'stem': stem,
                        'category': 'usecase',
                        'label': label,
                        'icon': '🖱️',
                        'title': extract_title(text) or label,
                        'summary': extract_summary(text),
                        'url': f'projects/{repo["id"]}/impact/usecase/{stem}.html',
                        'text': text,
                    })

        # ── ENGenius artifacts: artifacts/*.md ───────────────────────────────
        art_path = repo.get('artifacts_path') or (project_path / 'artifacts')
        if art_path and art_path.exists():
            for p in sorted(art_path.glob('*.md')):
                if p.name in ('README.md',):
                    continue
                stem = p.stem
                label, icon = ARTIFACT_LABELS.get(stem, (stem.replace('_', ' ').replace('-', ' ').title(), '📋'))
                text = p.read_text(encoding='utf-8', errors='replace')
                docs.append({
                    'repo_id': repo['id'],
                    'path': p,
                    'stem': stem,
                    'category': 'artifact',
                    'label': label,
                    'icon': icon,
                    'title': extract_title(text) or label,
                    'summary': extract_summary(text),
                    'url': f'projects/{repo["id"]}/artifacts/{stem}.html',
                    'text': text,
                })

            # ── ENGenius test_spec: artifacts/test_spec/*.md ─────────────────
            ts_path = art_path / 'test_spec'
            if ts_path.exists():
                for p in sorted(ts_path.glob('*.md')):
                    stem = p.stem
                    label, icon = TEST_SPEC_LABELS.get(stem, (stem.replace('-', ' ').replace('_', ' ').title(), '🧪'))
                    text = p.read_text(encoding='utf-8', errors='replace')
                    docs.append({
                        'repo_id': repo['id'],
                        'path': p,
                        'stem': stem,
                        'category': 'test_spec',
                        'label': label,
                        'icon': icon,
                        'title': extract_title(text) or label,
                        'summary': extract_summary(text),
                        'url': f'projects/{repo["id"]}/test_spec/{stem}.html',
                        'text': text,
                    })

    return docs

# ═══════════════════════════════════════════════════════════
#  MONGODB EXTRACTOR (da 08_data.md — no inference)
# ═══════════════════════════════════════════════════════════

def extract_mongo_info(docs):
    """Extract MongoDB collections info from 08_data.md of a project."""
    data_doc = next((d for d in docs if d['stem'] == '08_data'), None)
    if not data_doc:
        return {'collections': [], 'erd_mermaid': '', 'flow_mermaid': ''}
    
    text = data_doc['text']
    collections = []
    
    # extract collections table (Physical Data Model section)
    tbl_match = re.search(r'###.*Collections?\s*\n\s*\n(\|.+\|[\s\S]+?)(?=\n\n|\n##|$)', text)
    if tbl_match:
        tbl = tbl_match.group(1)
        for m in re.finditer(r'\|\s*`?([^|`]+)`?\s*\|\s*`?([^|`]*)`?\s*\|\s*([^|]*)\s*\|', tbl):
            cname = m.group(1).strip().strip('`')
            cls = m.group(2).strip().strip('`')
            note = m.group(3).strip()
            if cname and cname.lower() not in ('collection', 'classe', 'class', 'entity', '---'):
                collections.append({'name': cname, 'class': cls, 'note': note})

    # also look for inline mentions in Core logical entities table
    ent_match = re.search(r'###.*[Cc]ore.*entities?\s*\n\s*\n(\|.+\|[\s\S]+?)(?=\n\n|\n##|$)', text)
    if ent_match and not collections:
        tbl = ent_match.group(1)
        for m in re.finditer(r'\|\s*`([^`]+)`\s*\|\s*([^|]+)\|', tbl):
            cname = m.group(1).strip()
            note = m.group(2).strip()
            if cname and not cname.startswith('-'):
                collections.append({'name': cname, 'class': '', 'note': note})

    # extract ERD mermaid block
    erd = ''
    for m in re.finditer(r'```mermaid\n(.*?)```', text, re.DOTALL):
        code = m.group(1)
        if 'erDiagram' in code:
            erd = code.strip()
            break

    # extract flowchart (architecture) mermaid
    flow = ''
    for m in re.finditer(r'```mermaid\n(.*?)```', text, re.DOTALL):
        code = m.group(1)
        if any(k in code for k in ('flowchart', 'graph LR', 'graph TD')):
            flow = code.strip()
            break

    return {'collections': collections, 'erd_mermaid': erd, 'flow_mermaid': flow}

# ═══════════════════════════════════════════════════════════
#  CSS + JS  —  caricati da assets/ al momento dell'esecuzione
#  Vedi _load_asset() nella sezione CONFIG LOADING
# ═══════════════════════════════════════════════════════════

# ═══════════════════════════════════════════════════════════
#  HTML PAGE BUILDERS
# ═══════════════════════════════════════════════════════════

def _base(depth):
    """Return relative path prefix to site root."""
    return '../' * depth

def _cdn_scripts():
    return """
  <script src="https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/svg-pan-zoom@3.6.1/dist/svg-pan-zoom.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/lunr@2.3.9/lunr.min.js"></script>"""

def _sidebar(repos_data, current_url, base, all_docs_by_repo, site_cfg=None):
    site_title = (site_cfg or {}).get('title', 'Docs')
    site_desc  = (site_cfg or {}).get('description', 'Portfolio Documentazione Tecnica')

    parent_repo  = next((r for r in repos_data if r.get('type') == 'parent'), None)
    non_parent   = [r for r in repos_data if r.get('type') != 'parent']

    # ── Group non-parent repos by type ───────────────────────
    _TYPE_INFO = {
        'backend':  ('⚙️', 'Backend'),
        'frontend': ('🖥️', 'Frontend'),
        'bff':      ('🔀', 'BFF / Gateway'),
        'service':  ('⚡', 'Service'),
        'mobile':   ('📱', 'Mobile'),
    }
    from collections import OrderedDict
    groups = OrderedDict()
    for repo in non_parent:
        t = repo.get('type', 'service')
        groups.setdefault(t, []).append(repo)

    parts = []
    parts.append(f'''<nav id="sidebar">
  <div class="sidebar-logo">
    <div class="sidebar-logo-text">
      <a href="{base}index.html">🏠 <span>{h(site_title)}</span></a>
      <span class="logo-sub">{h(site_desc[:50])}</span>
    </div>
    <button id="sidebar-toggle" title="Chiudi menu">◀</button>
  </div>''')

    # ── Portfolio links ──────────────────────────────────────
    mongo_link = ''
    if any(
        any(d['stem'] == '08_data' for d in all_docs_by_repo.get(r['id'], []))
        for r in non_parent
    ):
        mongo_link = f'      <a href="{base}mongodb.html">🗄️ MongoDB</a>\n'

    parts.append(f'''  <div class="sidebar-section">
    <span class="sidebar-section-title">🌐 Portfolio</span>
    <div class="sidebar-direct">
      <a href="{base}index.html">📋 Home</a>
{mongo_link}      <a href="{base}search.html">🔍 Ricerca</a>
    </div>
  </div>''')

    # ── Filter input (shown only if > 4 projects) ────────────
    if len(non_parent) > 4:
        parts.append('''  <div class="sidebar-filter">
    <input id="sidebar-filter-input" type="search" placeholder="🔍 Filtra progetti…" autocomplete="off">
  </div>''')

    # ── Enterprise section ───────────────────────────────────
    if parent_repo:
        parent_docs = all_docs_by_repo.get(parent_repo['id'], [])
        ent_docs = [d for d in parent_docs if d['category'] == 'enterprise']
        req_docs = [d for d in parent_docs if d['category'] == 'requirement_coverage']
        if ent_docs or req_docs:
            is_ent_open = 'enterprise' in current_url or 'requirements' in current_url
            parts.append(f'''  <div class="sidebar-section sidebar-type-group" data-group="enterprise">
    <span class="sidebar-type-title">📊 Enterprise</span>
    <details class="sidebar-proj" {'open' if is_ent_open else ''}
             data-pid="enterprise" data-plabel="Enterprise">
      <summary>📊 Documentazione Enterprise</summary>
      <ul>''')
            for d in ent_docs:
                active = 'active' if d['url'] == current_url else ''
                parts.append(f'        <li><a href="{base}{d["url"]}" class="{active}">{d["icon"]} {d["label"]}</a></li>')
            if req_docs:
                parts.append('        <li class="sidebar-subgroup-title">📋 Requisiti</li>')
                for d in req_docs:
                    active = 'active' if d['url'] == current_url else ''
                    parts.append(f'        <li><a href="{base}{d["url"]}" class="{active}">{d["icon"]} {d["label"]}</a></li>')
            parts.append('      </ul>\n    </details>\n  </div>')

    # ── Projects grouped by type ─────────────────────────────
    for type_key, repos_in_group in groups.items():
        type_icon, type_label = _TYPE_INFO.get(type_key, ('📦', type_key.capitalize()))
        n = len(repos_in_group)
        # Open the group if any project in it is the current page
        group_has_active = any(
            any(d['url'] == current_url for d in all_docs_by_repo.get(r['id'], []))
            or f'projects/{r["id"]}' in current_url
            for r in repos_in_group
        )
        group_open = group_has_active or n <= 4

        parts.append(f'''  <div class="sidebar-section sidebar-type-group" data-group="{type_key}">
    <span class="sidebar-type-title">{type_icon} {type_label} <span class="proj-count">{n}</span></span>''')

        for repo in repos_in_group:
            repo_docs = all_docs_by_repo.get(repo['id'], [])
            main_docs = [d for d in repo_docs if d['category'] == 'main']
            proc_docs = [d for d in repo_docs if d['category'] == 'process']
            dd_docs   = [d for d in repo_docs if d['category'] == 'deepdive']
            uc_docs   = [d for d in repo_docs if d['category'] == 'usecase']
            art_docs  = [d for d in repo_docs if d['category'] == 'artifact']
            ts_docs   = [d for d in repo_docs if d['category'] == 'test_spec']

            is_proj_active = (
                any(d['url'] == current_url for d in repo_docs)
                or f'projects/{repo["id"]}' in current_url
            )
            proj_open = is_proj_active

            # Compact doc-count badges for collapsed state
            meta_badges = ''
            if main_docs:   meta_badges += f'<span class="proj-meta-badge">📚{len(main_docs)}</span>'
            if art_docs:    meta_badges += f'<span class="proj-meta-badge">📋{len(art_docs)}</span>'
            if proc_docs:   meta_badges += f'<span class="proj-meta-badge">↔️{len(proc_docs)}</span>'
            if dd_docs:     meta_badges += f'<span class="proj-meta-badge">🔎{len(dd_docs)}</span>'
            if ts_docs:     meta_badges += f'<span class="proj-meta-badge">🧪{len(ts_docs)}</span>'
            if uc_docs:     meta_badges += f'<span class="proj-meta-badge">🖱️{len(uc_docs)}</span>'

            dot = f'<span style="width:7px;height:7px;border-radius:50%;background:var(--c-{repo["color"]});display:inline-block;flex-shrink:0"></span>'

            parts.append(f'''    <details class="sidebar-proj" {'open' if proj_open else ''}
             data-pid="{h(repo['id'])}" data-plabel="{h(repo['label'])}">
      <summary>
        {dot}
        <span class="proj-summary-text">{h(repo["label"])}</span>
        <span class="proj-meta">{meta_badges}</span>
      </summary>
      <ul>
        <li><a href="{base}projects/{repo['id']}/index.html" class="{'active' if current_url == f'projects/{repo["id"]}/index.html' else ''}">🏠 Panoramica</a></li>''')

            # Main docs (up to 6, then "… +N altri")
            for d in main_docs[:6]:
                active = 'active' if d['url'] == current_url else ''
                parts.append(f'        <li><a href="{base}{d["url"]}" class="{active}">{d["icon"]} {d["label"]}</a></li>')
            if len(main_docs) > 6:
                parts.append(f'        <li><a href="{base}projects/{repo["id"]}/index.html" style="font-size:.72rem;color:var(--c-light)">… +{len(main_docs)-6} altri</a></li>')

            # Section links (only counts + anchor links, no individual doc links)
            def _sec(anchor, icon, label, docs):
                if not docs: return
                # If one of these docs is current, show the individual links too
                any_active = any(d['url'] == current_url for d in docs)
                if any_active:
                    parts.append(f'        <li class="sidebar-subgroup-title">{icon} {label}</li>')
                    for d in docs[:5]:
                        active = 'active' if d['url'] == current_url else ''
                        parts.append(f'        <li><a href="{base}{d["url"]}" class="{active}" style="font-size:.74rem">{h(d["label"][:28])}</a></li>')
                    if len(docs) > 5:
                        parts.append(f'        <li><a href="{base}projects/{repo["id"]}/index.html#{anchor}" style="font-size:.72rem;color:var(--c-light)">… +{len(docs)-5} altri</a></li>')
                else:
                    parts.append(f'        <li><a href="{base}projects/{repo["id"]}/index.html#{anchor}" style="font-size:.76rem;color:var(--c-muted)">{icon} {label} ({len(docs)})</a></li>')

            _sec('artifacts', '📋', 'Artefatti', art_docs)
            _sec('test-spec', '🧪', 'Test Spec', ts_docs)
            _sec('processi',  '↔️', 'Processi',  proc_docs)
            _sec('deepdive',  '🔎', 'Deep Dive', dd_docs)
            _sec('usecases',  '🖱️', 'Use Cases', uc_docs)

            parts.append('      </ul>\n    </details>')

        parts.append('  </div>')  # close sidebar-type-group

    parts.append('</nav>')
    return '\n'.join(parts)

def _page_shell(title, body, sidebar_html, base, depth=0, current_url='', site_title='Docs'):
    return f'''<!DOCTYPE html>
<html lang="it">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{h(title)} — {h(site_title)}</title>
  <link rel="stylesheet" href="{base}assets/style.css">
</head>
<body>
<div class="layout">
{sidebar_html}
  <main class="main-content">
{body}
  </main>
</div>
<button id="theme-toggle" title="Cambia tema">☀️</button>
<footer class="page-footer">
  <div>{h(site_title)} · Generato il {GEN_DATE} da analisi automatica · <a href="{base}index.html">Home</a></div>
</footer>
<script src="{base}assets/search-index.js"></script>{_cdn_scripts()}
<script src="{base}assets/app.js"></script>
</body>
</html>'''

# ── Home page ──────────────────────────────────────────────

def _tech_badge(tech: str) -> str:
    """Return a colored badge HTML span for a technology string."""
    sl = tech.lower()
    if any(k in sl for k in ('java','spring','maven','gradle','quarkus','micronaut')): cls = 'b-orange'
    elif any(k in sl for k in ('angular','react','vue','typescript','npm','node','next','svelte')): cls = 'b-blue'
    elif any(k in sl for k in ('mongodb','postgres','mysql','redis','elasticsearch','neo4j','cassandra')): cls = 'b-green'
    elif any(k in sl for k in ('kafka','rabbitmq','pulsar','nats','activemq')): cls = 'b-orange'
    elif any(k in sl for k in ('docker','k8s','kubernetes','aws','azure','gcp','terraform','nginx')): cls = 'b-gray'
    elif any(k in sl for k in ('oidc','oauth','pkce','auth','jwt','keycloak','okta')): cls = 'b-purple'
    elif any(k in sl for k in ('fhir','hapi','hl7','dicom','ihe')): cls = 'b-red'
    elif any(k in sl for k in ('python','django','flask','fastapi')): cls = 'b-teal'
    else: cls = 'b-gray'
    return f'<span class="badge {cls}">{h(tech)}</span>'

def _tb_cls(s: str) -> str:
    """Return CSS class for a stack tech badge (card footer)."""
    sl = s.lower()
    if any(k in sl for k in ('java','spring','maven','gradle')): return 'tb-java'
    if any(k in sl for k in ('angular','typescript','primeng','fullcalendar','npm','react','vue')): return 'tb-ts'
    if any(k in sl for k in ('mongo','redis','postgres','mysql','elastic','db','atlas')): return 'tb-db'
    if any(k in sl for k in ('docker','nginx','kafka','aws','azure','k8s','container','terraform')): return 'tb-infra'
    if any(k in sl for k in ('oidc','oauth','pkce','auth','jwt','keycloak')): return 'tb-auth'
    if any(k in sl for k in ('fhir','hapi','hl7')): return 'tb-fhir'
    return 'tb-infra'

def gen_home(site_cfg, repos, all_docs_by_repo):
    title       = site_cfg.get('title', 'Portfolio Documentazione Tecnica')
    description = site_cfg.get('description', '')

    total_docs    = sum(len(v) for v in all_docs_by_repo.values())
    non_parent    = [r for r in repos if r.get('type') != 'parent']
    parent_repo   = next((r for r in repos if r.get('type') == 'parent'), None)

    # ── Enterprise / landscape data ──────────────────────────
    parent_docs   = all_docs_by_repo.get(parent_repo['id'], []) if parent_repo else []
    ent_docs      = [d for d in parent_docs if d['category'] == 'enterprise']
    portfolio_doc = next((d for d in parent_docs if d['stem'] == '00_portfolio_overview'), None)
    landscape_doc = next((d for d in parent_docs if d['stem'] == '02_system_landscape'), None)

    portfolio_summary = ''
    if portfolio_doc:
        text = portfolio_doc['text']
        m = re.search(r'## 1\. Executive Summary\s*\n\s*\n([\s\S]+?)(?=\n## |\n# )', text)
        if m:
            portfolio_summary = m.group(1).strip()[:800]

    landscape_mermaid = ''
    if landscape_doc:
        for m in re.finditer(r'```mermaid\n(.*?)```', landscape_doc['text'], re.DOTALL):
            code = m.group(1)
            if 'subgraph' in code or 'flowchart' in code:
                landscape_mermaid = code.strip()
                break

    # ── Dynamic tech badge row from all projects ─────────────
    seen_tech = set()
    badges_html = ''
    for repo in non_parent:
        for t in repo['stack']:
            if t not in seen_tech:
                seen_tech.add(t)
                badges_html += _tech_badge(t) + '\n    '

    # ── Project cards ────────────────────────────────────────
    def _card_footer_links(repo, repo_docs):
        links = [f'<a href="projects/{repo["id"]}/index.html">Panoramica</a>']
        main_stems = {d['stem'] for d in repo_docs if d['category'] == 'main'}
        for stem, lbl in [('00_deep_dive','Deep Dive'),('08_data','Dati'),('06_software_architecture','Architettura')]:
            if stem in main_stems:
                links.append(f'<a href="projects/{repo["id"]}/{stem}.html">{lbl}</a>')
        if any(d['category'] == 'artifact' for d in repo_docs):
            links.append(f'<a href="projects/{repo["id"]}/index.html#artifacts">Artefatti</a>')
        if any(d['category'] == 'process' for d in repo_docs):
            links.append(f'<a href="projects/{repo["id"]}/index.html#processi">Processi</a>')
        return ''.join(links)

    cards_html = ''
    for repo in non_parent:
        color  = repo['color']
        cb_cls = f"cb-{color if color not in ('parent','service') else 'legacy'}"
        dot_cls = f"dot-{color if color not in ('parent','service') else 'legacy'}"
        stack_html = ''.join(f'<span class="tb {_tb_cls(s)}">{h(s)}</span>' for s in repo['stack'])
        repo_docs  = all_docs_by_repo.get(repo['id'], [])
        n_main    = len([d for d in repo_docs if d['category'] == 'main'])
        n_impact  = len([d for d in repo_docs if d['category'] in ('process','deepdive','usecase')])
        n_artif   = len([d for d in repo_docs if d['category'] in ('artifact','test_spec')])
        doc_meta  = f'{n_main} docs IMPACT'
        if n_impact: doc_meta += f' · {n_impact} impact'
        if n_artif:  doc_meta += f' · {n_artif} artefatti ENGenius'
        footer_links = _card_footer_links(repo, repo_docs)
        cards_html += f'''
      <div class="project-card" onclick="location.href='projects/{repo['id']}/index.html'">
        <div class="card-header">
          <div class="card-dot {dot_cls}"></div>
          <div class="card-title-area">
            <div class="card-name">{h(repo['label'])}</div>
            <div class="card-fullname">{h(repo['name'])}</div>
          </div>
          <span class="card-badge {cb_cls}">{h(repo['badge'])}</span>
        </div>
        <div class="card-body">
          <p class="card-desc">{h(repo['desc'])}</p>
          <div class="card-label">Stack</div>
          <div class="tech-row">{stack_html}</div>
          <div class="card-label">Documenti</div>
          <div style="font-size:.78rem;color:var(--c-muted)">{doc_meta}</div>
        </div>
        <div class="card-footer">
          {footer_links}
        </div>
      </div>'''

    # ── System Landscape section (optional) ──────────────────
    landscape_section = ''
    if landscape_mermaid:
        uid = _next_mmd()
        landscape_section = f'''
<section id="architettura">
  <div class="container">
    <h2 class="section-title">🌐 Architettura di Sistema</h2>
    <div class="mermaid-wrap" id="{uid}-wrap">
      <div class="mermaid-toolbar">
        <div class="diag-title-area">
          <h1>System Landscape — C4 Enterprise</h1>
          <p class="diag-desc">Scroll per zoom &bull; Drag per navigare</p>
        </div>
        <button class="toolbar-btn" onclick="pzIn('{uid}')">🔍 Zoom +</button>
        <button class="toolbar-btn" onclick="pzOut('{uid}')">🔍 Zoom −</button>
        <button class="toolbar-btn" onclick="pzReset('{uid}')">↺ Reset</button>
        <button class="toolbar-btn" onclick="pzFull('{uid}')">⛶ Fullscreen</button>
        <button class="toolbar-btn toolbar-btn-primary" onclick="pzSvg('{uid}')">⬇ SVG</button>
      </div>
      <div class="mermaid-canvas" id="{uid}-canvas">
        <div class="mermaid" id="{uid}">{h(landscape_mermaid)}</div>
        <div class="zoom-hint">Scroll: zoom &bull; Drag: pan</div>
      </div>
    </div>
    <p style="font-size:.8rem;color:var(--c-muted);margin-top:.5rem">Fonte: <a href="enterprise/02_system_landscape.html">enterprise/02_system_landscape.md</a></p>
  </div>
</section>'''

    # ── MongoDB section (conditional) ────────────────────────
    has_mongo = any(
        any(d['stem'] == '08_data' for d in all_docs_by_repo.get(r['id'], []))
        for r in non_parent
    )
    mongo_section = ''
    if has_mongo:
        mongo_section = f'''
<section id="mongodb-preview">
  <div class="container">
    <h2 class="section-title">🗄️ Relazioni MongoDB</h2>
    <p style="color:var(--c-muted);margin-bottom:1rem">Inventario delle collection MongoDB per progetto con ownership e relazioni tra entità.</p>
    <div style="display:flex;flex-wrap:wrap;gap:.8rem">
      <a href="mongodb.html" style="display:inline-flex;align-items:center;gap:8px;background:var(--c-surface);border:1px solid var(--c-border);border-radius:var(--radius);padding:12px 20px;font-weight:600;color:var(--c-accent);text-decoration:none;font-size:.9rem">🗄️ Visualizza relazioni MongoDB →</a>
    </div>
  </div>
</section>'''

    # ── Enterprise section (conditional) ─────────────────────
    enterprise_section = ''
    if ent_docs:
        ent_links = ''.join(f'<a class="resource-link" href="{d["url"]}">{d["icon"]} {h(d["label"])}</a>\n      ' for d in ent_docs)
        enterprise_section = f'''
<section id="enterprise">
  <div class="container">
    <h2 class="section-title">📊 Documentazione Enterprise</h2>
    <div style="display:flex;flex-wrap:wrap;gap:4px">
      {ent_links}
    </div>
  </div>
</section>'''

    # ── Summary box ───────────────────────────────────────────
    if portfolio_summary:
        summary_html = md_bold(portfolio_summary)
    elif description:
        summary_html = h(description)
    else:
        summary_html = f'<strong>{h(title)}</strong> — {len(non_parent)} progetti documentati tramite ENGenius/IMPACT.'

    # ── Dynamic top nav ───────────────────────────────────────
    nav_items = [
        '<li><a href="#panoramica">📋 Panoramica</a></li>',
        '<li><a href="#progetti">📦 Progetti</a></li>',
    ]
    if landscape_mermaid:
        nav_items.insert(1, '<li><a href="#architettura">🌐 Architettura</a></li>')
    if has_mongo:
        nav_items.append('<li><a href="mongodb.html">🗄️ MongoDB</a></li>')
    if ent_docs:
        nav_items.append('<li><a href="#enterprise">📊 Enterprise</a></li>')
    nav_items.append('<li><a href="search.html">🔍 Ricerca</a></li>')
    top_nav_items = '\n      '.join(nav_items)

    # ── Stats ─────────────────────────────────────────────────
    stats_items = [
        f'<div class="stat-item"><div class="stat-value">{len(non_parent)}</div><div class="stat-label">Progetti</div></div>',
        f'<div class="stat-item"><div class="stat-value">{total_docs}</div><div class="stat-label">Documenti</div></div>',
    ]
    if ent_docs:
        stats_items.append(f'<div class="stat-item"><div class="stat-value">{len(ent_docs)}</div><div class="stat-label">Enterprise Docs</div></div>')
    stats_html = '\n      '.join(stats_items)

    sidebar_html = _sidebar(repos, 'index.html', '', all_docs_by_repo, site_cfg)

    return f'''<!DOCTYPE html>
<html lang="it">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{h(title)}</title>
  <link rel="stylesheet" href="assets/style.css">
  <style>
    .resource-link{{display:inline-flex;align-items:center;gap:6px;background:var(--c-surface);border:1px solid var(--c-border);border-radius:var(--radius);padding:9px 16px;text-decoration:none;color:var(--c-text);font-size:.875rem;font-weight:500;transition:background .15s,border-color .15s;margin:4px}}
    .resource-link:hover{{background:rgba(56,189,248,.08);border-color:rgba(56,189,248,.35);color:var(--c-accent);text-decoration:none}}
  </style>
</head>
<body>
<div class="layout">
{sidebar_html}
<div style="flex:1;overflow-y:auto">

<header class="site-header">
  <div class="container header-inner">
    <div class="header-eyebrow">Documentazione Tecnica · ENGenius/IMPACT</div>
    <h1>{h(title)}</h1>
    {f'<p class="header-meta">{h(description)}</p>' if description else ''}
    <div class="badge-row">
    {badges_html}
    </div>
  </div>
</header>

<nav class="top-nav">
  <div class="container">
    <ul>
      {top_nav_items}
    </ul>
  </div>
</nav>

<section id="panoramica">
  <div class="container">
    <h2 class="section-title">📋 Panoramica Portfolio</h2>
    <div class="stats-bar">
      {stats_html}
    </div>
    <div class="summary-box">
      {summary_html}
    </div>
  </div>
</section>

{landscape_section}

<section id="progetti">
  <div class="container">
    <h2 class="section-title">📦 Progetti</h2>
    <div class="projects-grid">
      {cards_html}
    </div>
  </div>
</section>

{mongo_section}

{enterprise_section}

<button id="theme-toggle" title="Cambia tema">☀️</button>
<footer>
  <div class="container">
    <p>{h(title)} — Generato il {GEN_DATE} da analisi automatica | ENGenius/IMPACT Static Site Generator</p>
  </div>
</footer>

</div><!-- flex wrapper -->
</div><!-- layout -->
<script src="assets/search-index.js"></script>{_cdn_scripts()}
<script src="assets/app.js"></script>
</body>
</html>'''

# ── Project overview page ──────────────────────────────────

def gen_project_page(repo, docs, all_docs_by_repo, repos=None, site_cfg=None):
    base = '../../'
    main_docs   = [d for d in docs if d['category'] == 'main']
    proc_docs   = [d for d in docs if d['category'] == 'process']
    dd_docs     = [d for d in docs if d['category'] == 'deepdive']
    uc_docs     = [d for d in docs if d['category'] == 'usecase']
    art_docs    = [d for d in docs if d['category'] == 'artifact']
    ts_docs     = [d for d in docs if d['category'] == 'test_spec']
    
    # read deep dive for executive summary
    deep_doc = next((d for d in docs if d['stem'] == '00_deep_dive'), None)
    exec_summary = ''
    if deep_doc:
        m = re.search(r'## 1\. Executive Summary\s*\n\s*\n([\s\S]+?)(?=\n## |\n---)', deep_doc['text'])
        if m:
            exec_summary = m.group(1).strip()
            if len(exec_summary) > 900:
                exec_summary = exec_summary[:900] + '…'

    # mongodb info
    mongo_info = extract_mongo_info(docs)
    collections = mongo_info['collections']

    # doc cards for main docs
    doc_cards_html = ''
    for d in main_docs:
        doc_cards_html += f'''
      <a class="doc-card" href="../../{d['url']}">
        <div class="doc-card-icon">{d['icon']}</div>
        <div class="doc-card-label">{h(d['label'])}</div>
        <div class="doc-card-summary">{md_bold(d['summary'][:150]) if d['summary'] else ''}</div>
      </a>'''

    # architecture mermaid from 00_deep_dive or 06
    arch_mermaid = ''
    for stem in ('06_software_architecture', '00_deep_dive', '01_context'):
        src_doc = next((d for d in docs if d['stem'] == stem), None)
        if src_doc:
            for m in re.finditer(r'```mermaid\n(.*?)```', src_doc['text'], re.DOTALL):
                code = m.group(1)
                if any(k in code for k in ('flowchart', 'graph LR', 'graph TD')):
                    arch_mermaid = code.strip()
                    break
        if arch_mermaid:
            break

    arch_section = ''
    if arch_mermaid:
        uid = _next_mmd()
        arch_section = f'''<h2>🏗️ Architettura</h2>
    <div class="mermaid-wrap" id="{uid}-wrap">
      <div class="mermaid-toolbar">
        <div class="diag-title-area">
          <h1>Architecture overview — {h(repo["label"])}</h1>
          <p class="diag-desc">Scroll per zoom &bull; Drag per navigare</p>
        </div>
        <button class="toolbar-btn" onclick="pzIn('{uid}')">🔍 Zoom +</button>
        <button class="toolbar-btn" onclick="pzOut('{uid}')">🔍 Zoom −</button>
        <button class="toolbar-btn" onclick="pzReset('{uid}')">↺ Reset</button>
        <button class="toolbar-btn" onclick="pzFull('{uid}')">⛶ Fullscreen</button>
        <button class="toolbar-btn toolbar-btn-primary" onclick="pzSvg('{uid}')">⬇ SVG</button>
      </div>
      <div class="mermaid-canvas" id="{uid}-canvas">
        <div class="mermaid" id="{uid}">{h(arch_mermaid)}</div>
        <div class="zoom-hint">Scroll: zoom &bull; Drag: pan</div>
      </div>
    </div>'''

    mongo_section = ''
    if collections:
        items = ''.join(f'<li><code>{h(c["name"])}</code> <span class="coll-note">{h(c.get("note",""))}</span></li>' for c in collections)
        mongo_section = f'''<h2>🗄️ MongoDB Collections</h2>
    <ul class="collection-list">{items}</ul>
    <p style="margin-top:.5rem"><a href="../../{next((d["url"] for d in docs if d["stem"]=="08_data"), "#")}">→ Vedi modello dati completo</a></p>'''

    # impact docs
    proc_section = ''
    if proc_docs:
        links = ''.join(f'<a class="doc-card" href="../../{d["url"]}"><div class="doc-card-icon">↔️</div><div class="doc-card-label">{h(d["label"][:40])}</div></a>' for d in proc_docs)
        proc_section = f'<h2 id="processi">↔️ Processi ({len(proc_docs)})</h2><div class="doc-cards">{links}</div>'

    dd_section = ''
    if dd_docs:
        links = ''.join(f'<a class="doc-card" href="../../{d["url"]}"><div class="doc-card-icon">🔎</div><div class="doc-card-label">{h(d["label"][:40])}</div></a>' for d in dd_docs)
        dd_section = f'<h2 id="deepdive">🔎 Deep Dive ({len(dd_docs)})</h2><div class="doc-cards">{links}</div>'

    color = repo['color']
    cb_cls = f"cb-{color if color != 'parent' else 'legacy'}"

    # Badge colorati per lo stack (stessa logica della home)
    def _tb(s):
        sl = s.lower()
        if any(k in sl for k in ('java','spring','maven')): cls = 'tb-java'
        elif any(k in sl for k in ('angular','typescript','primeng','fullcalendar','npm')): cls = 'tb-ts'
        elif any(k in sl for k in ('mongo','redis','db','atlas')): cls = 'tb-db'
        elif any(k in sl for k in ('docker','nginx','kafka','aws','k8s','container')): cls = 'tb-infra'
        elif any(k in sl for k in ('oidc','oauth','pkce','auth','jwt')): cls = 'tb-auth'
        elif any(k in sl for k in ('fhir','hapi','hl7')): cls = 'tb-fhir'
        else: cls = 'tb-infra'
        return f'<span class="tb {cls}">{h(s)}</span>'
    stack_badges = ''.join(_tb(s) for s in repo['stack'])

    # Process section con entry point
    proc_section = ''
    if proc_docs:
        proc_cards = ''
        for d in proc_docs:
            ep = d.get('entry_point', '')
            ep_html = f'<div class="proc-card-ep">{h(ep)}</div>' if ep else ''
            proc_cards += f'''<a class="proc-card" href="../../{d['url']}">
          <div class="proc-card-name">↔️ {h(d['label'])}</div>
          {ep_html}
        </a>'''
        proc_section = f'<h2 id="processi">↔️ Processi ({len(proc_docs)})</h2><div class="proc-cards">{proc_cards}</div>'

    dd_section = ''
    if dd_docs:
        links = ''.join(f'<a class="doc-card" href="../../{d["url"]}"><div class="doc-card-icon">🔎</div><div class="doc-card-label">{h(d["label"][:40])}</div></a>' for d in dd_docs)
        dd_section = f'<h2 id="deepdive">🔎 Deep Dive ({len(dd_docs)})</h2><div class="doc-cards">{links}</div>'

    uc_section = ''
    if uc_docs:
        links = ''.join(f'<a class="doc-card" href="../../{d["url"]}"><div class="doc-card-icon">🖱️</div><div class="doc-card-label">{h(d["label"][:40])}</div></a>' for d in uc_docs)
        uc_section = f'<h2 id="usecases">🖱️ Use Cases ({len(uc_docs)})</h2><div class="doc-cards">{links}</div>'

    art_section = ''
    if art_docs:
        links = ''.join(f'<a class="doc-card" href="../../{d["url"]}"><div class="doc-card-icon">{d["icon"]}</div><div class="doc-card-label">{h(d["label"][:40])}</div><div class="doc-card-summary">{md_bold(d["summary"][:100]) if d["summary"] else ""}</div></a>' for d in art_docs)
        art_section = f'<h2 id="artifacts">📋 Artefatti ENGenius ({len(art_docs)})</h2><div class="doc-cards">{links}</div>'

    ts_section = ''
    if ts_docs:
        links = ''.join(f'<a class="doc-card" href="../../{d["url"]}"><div class="doc-card-icon">{d["icon"]}</div><div class="doc-card-label">{h(d["label"][:40])}</div></a>' for d in ts_docs)
        ts_section = f'<h2 id="test-spec">🧪 Test Spec ({len(ts_docs)})</h2><div class="doc-cards">{links}</div>'

    sidebar = _sidebar(repos or [], f'projects/{repo["id"]}/index.html', base, all_docs_by_repo, site_cfg)
    site_title = (site_cfg or {}).get('title', 'Docs')

    body = f'''
    <div class="breadcrumb"><a href="{base}index.html">🏠 Home</a> <span class="sep">›</span> {h(repo["label"])}</div>
    <div class="page-header">
      <h1>{h(repo['label'])} <span class="card-badge {cb_cls}" style="font-size:.75rem;vertical-align:middle;margin-left:.5rem">{h(repo['badge'])}</span></h1>
      <p class="subtitle">{h(repo['name'])} · {h(repo['desc'])}</p>
      <div class="badge-row" style="margin-top:.6rem">
        {stack_badges}
      </div>
    </div>

    {f'<div class="summary-box"><strong>Executive Summary</strong><br>{md_bold(exec_summary)}</div>' if exec_summary else ''}

    {f'<h2>📚 Documenti Tecnici ({len(main_docs)})</h2><div class="doc-cards">{doc_cards_html}</div>' if main_docs else ''}

    {arch_section}
    {mongo_section}
    {art_section}
    {ts_section}
    {proc_section}
    {dd_section}
    {uc_section}
'''
    return _page_shell(f'{repo["label"]} — Panoramica', body, sidebar, base, depth=2,
                       current_url=f'projects/{repo["id"]}/index.html', site_title=site_title)

# ── Individual doc page ────────────────────────────────────

def gen_doc_page(doc, repo_or_none, all_docs_by_repo, repos=None, site_cfg=None):
    depth = doc['url'].count('/')
    base = _base(depth)
    
    repo_id = doc['repo_id']
    repo = next((r for r in (repos or []) if r['id'] == repo_id), None)
    site_title = (site_cfg or {}).get('title', 'Docs')
    
    sidebar = _sidebar(repos or [], doc['url'], base, all_docs_by_repo, site_cfg)
    
    # breadcrumb
    bc_parts = [f'<a href="{base}index.html">🏠 Home</a>']
    if repo and repo.get('type') != 'parent':
        bc_parts.append(f'<span class="sep">›</span><a href="{base}projects/{repo["id"]}/index.html">{h(repo["label"])}</a>')
    elif doc['category'] == 'enterprise':
        bc_parts.append('<span class="sep">›</span><a href="' + base + 'enterprise/index.html">Enterprise</a>')
    elif doc['category'] == 'requirement_coverage':
        bc_parts.append('<span class="sep">›</span><a href="' + base + 'enterprise/index.html">Requisiti</a>')
    bc_parts.append(f'<span class="sep">›</span>{h(doc["label"])}')
    breadcrumb = ''.join(bc_parts)

    # Per le pagine requirement_coverage: estrai la sezione "Fonti considerate"
    # dal testo markdown e spostala in fondo alla pagina
    fonti_section_html = ''
    md_text = doc['text']
    if doc['category'] == 'requirement_coverage':
        fonti_pattern = re.compile(
            r'(^## Fonti(?: considerate)?\s*\n[\s\S]+?)(?=^## |\Z)',
            re.MULTILINE
        )
        fonti_m = fonti_pattern.search(md_text)
        if fonti_m:
            fonti_md = fonti_m.group(1)
            fonti_section_html = (
                '<div class="fonti-block" style="margin-top:2.5rem;padding-top:1.5rem;'
                'border-top:2px solid var(--c-border)">'
                + md_to_html(fonti_md) +
                '</div>'
            )
            md_text = md_text[:fonti_m.start()] + md_text[fonti_m.end():]

    content_html = md_to_html(md_text)
    
    # Source file reference (relative to project path)
    try:
        src_ref = f'<code>{str(doc["path"])}</code>'
    except Exception:
        src_ref = ''
    
    body = f'''
    <div class="breadcrumb">{breadcrumb}</div>
    <div class="page-header">
      <h1>{doc["icon"]} {h(doc["title"])}</h1>
      {'<p class="subtitle">' + h(repo["label"]) + ' · ' + h(doc["label"]) + '</p>' if repo else ''}
    </div>
    <div class="doc-content">
      {content_html}
    </div>
    {fonti_section_html}
    <div style="margin-top:2rem;padding-top:1rem;border-top:1px solid var(--c-border);font-size:.8rem;color:var(--c-muted)">
      Fonte: {src_ref}
    </div>
'''
    return _page_shell(doc['title'], body, sidebar, base, depth=depth, current_url=doc['url'], site_title=site_title)

# ── MongoDB page ───────────────────────────────────────────

def gen_mongodb_page(all_repos, all_docs_by_repo, site_cfg=None):
    base = ''
    sidebar = _sidebar(all_repos, 'mongodb.html', base, all_docs_by_repo, site_cfg)
    site_title = (site_cfg or {}).get('title', 'Docs')

    sections = []
    all_collections_table = []

    for repo in all_repos:
        if repo.get('type') == 'parent':
            continue
        docs = all_docs_by_repo.get(repo['id'], [])
        info = extract_mongo_info(docs)
        colls = info['collections']
        erd   = info['erd_mermaid']
        flow  = info['flow_mermaid']

        if not colls and not erd and not flow:
            continue

        # table rows
        for c in colls:
            all_collections_table.append({'repo': repo['label'], 'name': c['name'], 'class': c.get('class',''), 'note': c.get('note','')})

        # section HTML
        colls_html = ''
        if colls:
            colls_html = '<ul class="collection-list">'
            for c in colls:
                note = f' <span class="coll-note">— {h(c["note"])}</span>' if c.get('note') else ''
                cls  = f' <span class="coll-note">({h(c["class"])})</span>' if c.get('class') else ''
                colls_html += f'<li><code>{h(c["name"])}</code>{cls}{note}</li>'
            colls_html += '</ul>'

        erd_html = ''
        if erd:
            uid = _next_mmd()
            erd_html = f'''<h3>Diagramma ER</h3>
      <div class="mermaid-wrap" id="{uid}-wrap">
        <div class="mermaid-toolbar">
          <div class="diag-title-area">
            <h1>Entity Relationship — {h(repo["label"])}</h1>
            <p class="diag-desc">Scroll per zoom &bull; Drag per navigare</p>
          </div>
          <button class="toolbar-btn" onclick="pzIn('{uid}')">🔍 Zoom +</button>
          <button class="toolbar-btn" onclick="pzOut('{uid}')">🔍 Zoom −</button>
          <button class="toolbar-btn" onclick="pzReset('{uid}')">↺ Reset</button>
          <button class="toolbar-btn" onclick="pzFull('{uid}')">⛶ Fullscreen</button>
          <button class="toolbar-btn toolbar-btn-primary" onclick="pzSvg('{uid}')">⬇ SVG</button>
        </div>
        <div class="mermaid-canvas" id="{uid}-canvas">
          <div class="mermaid" id="{uid}">{h(erd)}</div>
          <div class="zoom-hint">Scroll: zoom &bull; Drag: pan</div>
        </div>
      </div>'''

        data_url = next((d['url'] for d in docs if d['stem'] == '08_data'), '')
        color = repo['color']
        cb_cls = f"cb-{color}"
        sections.append(f'''
    <section id="{repo['id']}" style="padding:2rem 0;border-top:1px solid var(--c-border)">
      <h2><span class="card-badge {cb_cls}" style="font-size:.75rem;margin-right:.5rem">{h(repo['badge'])}</span>{h(repo["label"])}</h2>
      <p style="color:var(--c-muted);font-size:.88rem;margin-bottom:1rem">{h(repo["desc"])}</p>
      {('<h3>Collections</h3>' + colls_html) if colls else ''}
      {erd_html}
      {('<p style="margin-top:.5rem"><a href="' + data_url + '">→ 08_data.md — Modello dati completo</a></p>') if data_url else ''}
    </section>''')

    # cross-repo table
    tbl_rows = ''
    for row in all_collections_table:
        tbl_rows += f'<tr><td><strong>{h(row["repo"])}</strong></td><td><code>{h(row["name"])}</code></td><td><code>{h(row["class"])}</code></td><td>{h(row["note"][:80])}</td></tr>'

    body = f'''
    <div class="breadcrumb"><a href="index.html">🏠 Home</a> <span class="sep">›</span> MongoDB Relations</div>
    <div class="page-header">
      <h1>🗄️ Relazioni MongoDB</h1>
      <p class="subtitle">Inventario collections, ownership e relazioni tra entità per tutti i repository</p>
    </div>

    <h2>📊 Vista Cross-Repository</h2>
    <p style="color:var(--c-muted);font-size:.88rem;margin-bottom:1rem">
      Tutte le MongoDB collection identificate nei file <code>08_data.md</code> di ogni progetto.
      Nessuna inferenza: solo evidenze documentali.
    </p>
    <div class="table-wrap">
      <table>
        <thead><tr><th>Progetto</th><th>Collection</th><th>Entity Class</th><th>Note</th></tr></thead>
        <tbody>{tbl_rows}</tbody>
      </table>
    </div>

    {''.join(sections)}
'''
    return _page_shell('MongoDB Relations', body, sidebar, base, depth=0, current_url='mongodb.html', site_title=site_title)

# ── Search page ────────────────────────────────────────────

def gen_search_page(all_docs_by_repo, repos=None, site_cfg=None):
    base = ''
    sidebar = _sidebar(repos or [], 'search.html', base, all_docs_by_repo, site_cfg)
    site_title = (site_cfg or {}).get('title', 'Docs')

    # Dynamic search suggestion buttons from all stacks
    seen_terms = set()
    cat_btns = ''
    term_icons = {
        'MongoDB': '🗄️', 'PostgreSQL': '🗄️', 'Redis': '🔴', 'Kafka': '📨', 'RabbitMQ': '📨',
        'OIDC': '🔐', 'OAuth': '🔐', 'JWT': '🔐', 'FHIR': '🏥', 'HL7': '🏥',
        'Docker': '🐳', 'Kubernetes': '⚙️', 'AWS': '☁️', 'Spring': '🌱',
        'Angular': '🅰️', 'React': '⚛️', 'architettura': '🏗️', 'deployment': '🚀',
        'test': '🧪', 'requisiti': '📋',
    }
    for repo in (repos or []):
        for t in repo.get('stack', []):
            w = t.split()[0]  # first word of tech string
            if w and w not in seen_terms and len(w) > 2:
                seen_terms.add(w)
                icon = next((v for k, v in term_icons.items() if k.lower() in w.lower()), '🔍')
                cat_btns += f'<button class="cat-btn" data-term="{h(w)}">{icon} {h(w)}</button>\n      '
    # Add generic useful terms
    for term, icon in [('architettura','🏗️'), ('deployment','🚀'), ('test','🧪'), ('requisiti','📋')]:
        if term not in seen_terms:
            cat_btns += f'<button class="cat-btn" data-term="{term}">{icon} {term.capitalize()}</button>\n      '
    
    body = f'''
    <div class="breadcrumb"><a href="index.html">🏠 Home</a> <span class="sep">›</span> Ricerca</div>
    <div class="page-header">
      <h1>🔍 Ricerca</h1>
      <p class="subtitle">Cerca in tutta la documentazione del portfolio</p>
    </div>

    <div class="search-box">
      <span class="search-icon">🔍</span>
      <input id="search-input" type="search" placeholder="Es: architettura, deployment, test, use case…" autocomplete="off">
    </div>

    <div style="display:flex;gap:.5rem;flex-wrap:wrap;margin-bottom:1.5rem;align-items:center">
      <span style="font-size:.78rem;color:var(--c-muted)">Cerca per tema:</span>
      {cat_btns}
    </div>

    <div id="search-results">
      <p style="color:var(--c-muted)">Inserisci una parola chiave per cercare.</p>
    </div>
'''
    return _page_shell('Ricerca', body, sidebar, base, depth=0, current_url='search.html', site_title=site_title)

# ── Enterprise index page ──────────────────────────────────

def gen_enterprise_index(all_docs_by_repo, repos=None, site_cfg=None):
    base = ''
    parent_repo = next((r for r in (repos or []) if r.get('type') == 'parent'), None)
    parent_id = parent_repo['id'] if parent_repo else 'container'
    parent_docs = all_docs_by_repo.get(parent_id, [])
    ent_docs = [d for d in parent_docs if d['category'] == 'enterprise']
    req_docs = [d for d in parent_docs if d['category'] == 'requirement_coverage']
    site_title = (site_cfg or {}).get('title', 'Docs')

    sidebar = _sidebar(repos or [], 'enterprise/index.html', base, all_docs_by_repo, site_cfg)

    cards_ent  = ''.join(f'<a class="doc-card" href="../{d["url"]}"><div class="doc-card-icon">{d["icon"]}</div><div class="doc-card-label">{h(d["label"])}</div><div class="doc-card-summary">{md_bold(d["summary"][:120])}</div></a>' for d in ent_docs)
    cards_req  = ''.join(f'<a class="doc-card" href="../{d["url"]}"><div class="doc-card-icon">{d["icon"]}</div><div class="doc-card-label">{h(d["label"])}</div><div class="doc-card-summary">{md_bold(d["summary"][:120])}</div></a>' for d in req_docs)

    body = f'''
    <div class="breadcrumb"><a href="../index.html">🏠 Home</a> <span class="sep">›</span> Enterprise</div>
    <div class="page-header">
      <h1>📊 Documentazione Enterprise</h1>
      <p class="subtitle">Analisi cross-progetto del portfolio</p>
    </div>
    <h2>📊 Analisi Portfolio</h2>
    <div class="doc-cards">{cards_ent}</div>
    {('<h2>📋 Requisiti</h2><div class="doc-cards">' + cards_req + '</div>') if req_docs else ''}
'''
    return _page_shell('Enterprise Docs', body, sidebar, '../', depth=1, current_url='enterprise/index.html', site_title=site_title)

# ═══════════════════════════════════════════════════════════
#  SEARCH INDEX BUILDER
# ═══════════════════════════════════════════════════════════

def build_search_index(all_docs_flat):
    index = []
    cat_map = {
        'main':                 lambda d: DOC_LABELS.get(d['stem'], ('Doc',''))[0],
        'enterprise':           lambda d: 'Enterprise',
        'requirement_coverage': lambda d: 'Requisiti',
        'process':              lambda d: 'Processo',
        'deepdive':             lambda d: 'Deep Dive',
        'usecase':              lambda d: 'Use Case',
        'artifact':             lambda d: ARTIFACT_LABELS.get(d['stem'], ('Artefatto',''))[0],
        'test_spec':            lambda d: 'Test Spec',
    }
    for doc in all_docs_flat:
        content = re.sub(r'```[\s\S]*?```', ' ', doc['text'])
        content = re.sub(r'[#*`|_~>\[\]()]', ' ', content)
        content = re.sub(r'\s+', ' ', content).strip()[:3000]
        fn = cat_map.get(doc['category'])
        category = fn(doc) if fn else 'Doc'
        index.append({
            'id':       doc['url'].replace('/', '-').replace('.html', ''),
            'title':    doc['title'] or doc['label'],
            'project':  doc['repo_id'],
            'category': category,
            'url':      doc['url'],
            'content':  content,
        })
    return index

# ═══════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════

def write(path, content, out_dir):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')
    try:
        print(f'  ✓ {path.relative_to(out_dir)}')
    except ValueError:
        print(f'  ✓ {path}')

def main():
    global _mermaid_seq
    _mermaid_seq = 0

    args = _parse_args()

    # ── Load config ───────────────────────────────────────
    config_path = Path(args.config)
    if not config_path.is_absolute():
        config_path = Path.cwd() / config_path

    if not config_path.exists():
        print(f'❌  Config non trovato: {config_path}')
        print(f'   Crea un file site_config.yaml (vedi site_config.example.yaml)')
        sys.exit(1)

    config     = _load_config(config_path)
    config_dir = config_path.parent
    site_cfg   = config.get('site', {})

    # Output directory
    out_raw = site_cfg.get('output_dir', './docs')
    OUT = Path(out_raw) if Path(out_raw).is_absolute() else (config_dir / out_raw).resolve()

    # Repos
    repos_data = _build_repos(config.get('projects', []), config_dir)
    if not repos_data:
        print('❌  Nessun progetto in site_config.yaml. Aggiungi almeno un progetto.')
        sys.exit(1)

    # Filter to single project if --project flag used
    only_project = args.project
    if only_project and not any(r['id'] == only_project for r in repos_data):
        print(f'❌  Progetto "{only_project}" non trovato in site_config.yaml')
        sys.exit(1)

    # ── Load CSS / JS ──────────────────────────────────────
    css_content = _load_asset('default.css', override=args.css, config_override=site_cfg.get('css_file'))
    js_content  = _load_asset('default.js',  override=args.js,  config_override=site_cfg.get('js_file'))

    print(f'\n🔨  ENGenius/IMPACT Site Generator')
    print(f'    Config : {config_path}')
    print(f'    Output : {OUT}')
    if only_project:
        print(f'    Progetto: {only_project} (build incrementale)')
    print()

    # ── Clean + create output ──────────────────────────────
    if not only_project:
        if OUT.exists():
            shutil.rmtree(OUT)
    OUT.mkdir(parents=True, exist_ok=True)

    # ── Assets ────────────────────────────────────────────
    print('📦  Assets…')
    write(OUT / 'assets' / 'style.css', css_content, OUT)
    write(OUT / 'assets' / 'app.js',    js_content,  OUT)

    # ── Scan all docs ──────────────────────────────────────
    print('\n📄  Scanning docs…')
    all_docs_by_repo = {}
    all_docs_flat    = []

    for repo in repos_data:
        docs = scan_docs(repo)
        all_docs_by_repo[repo['id']] = docs
        all_docs_flat.extend(docs)
        cats = {}
        for d in docs:
            cats[d['category']] = cats.get(d['category'], 0) + 1
        cat_str = ', '.join(f'{v} {k}' for k, v in sorted(cats.items()))
        print(f'    {repo["id"]}: {len(docs)} docs ({cat_str or "nessuno"})')

    # ── Search index ───────────────────────────────────────
    if not only_project:
        print('\n🔍  Search index…')
        index_data = build_search_index(all_docs_flat)
        index_js = 'window.SITE_SEARCH_INDEX = ' + json.dumps(index_data, ensure_ascii=False) + ';'
        write(OUT / 'assets' / 'search-index.js', index_js, OUT)

    # ── Home ──────────────────────────────────────────────
    if not only_project:
        print('\n🏠  Home…')
        write(OUT / 'index.html', gen_home(site_cfg, repos_data, all_docs_by_repo), OUT)

        # ── Search page ─────────────────────────────────────
        print('🔍  Search page…')
        write(OUT / 'search.html', gen_search_page(all_docs_by_repo, repos=repos_data, site_cfg=site_cfg), OUT)

        # ── MongoDB page (conditional) ───────────────────────
        has_mongo = any(
            any(d['stem'] == '08_data' for d in all_docs_by_repo.get(r['id'], []))
            for r in repos_data if r.get('type') != 'parent'
        )
        if has_mongo:
            print('🗄️  MongoDB page…')
            write(OUT / 'mongodb.html', gen_mongodb_page(repos_data, all_docs_by_repo, site_cfg=site_cfg), OUT)

        # ── Enterprise index (conditional) ───────────────────
        parent_repo = next((r for r in repos_data if r.get('type') == 'parent'), None)
        if parent_repo:
            parent_docs = all_docs_by_repo.get(parent_repo['id'], [])
            if any(d['category'] == 'enterprise' for d in parent_docs):
                print('📊  Enterprise index…')
                write(OUT / 'enterprise' / 'index.html',
                      gen_enterprise_index(all_docs_by_repo, repos=repos_data, site_cfg=site_cfg), OUT)

    # ── Project pages ──────────────────────────────────────
    print('\n📦  Project pages…')
    for repo in repos_data:
        if repo.get('type') == 'parent':
            continue
        if only_project and repo['id'] != only_project:
            continue
        docs = all_docs_by_repo[repo['id']]
        write(OUT / 'projects' / repo['id'] / 'index.html',
              gen_project_page(repo, docs, all_docs_by_repo, repos=repos_data, site_cfg=site_cfg), OUT)

    # ── Individual doc pages ───────────────────────────────
    print('\n📃  Doc pages…')
    for doc in all_docs_flat:
        if only_project and doc['repo_id'] != only_project:
            continue
        write(OUT / doc['url'], gen_doc_page(doc, None, all_docs_by_repo, repos=repos_data, site_cfg=site_cfg), OUT)

    # ── Summary ───────────────────────────────────────────
    total = sum(1 for _ in OUT.rglob('*.html'))
    print(f'\n✅  Done! {total} HTML pages generated in {OUT}')
    print(f'    Open: file://{OUT}/index.html\n')

if __name__ == '__main__':
    main()
