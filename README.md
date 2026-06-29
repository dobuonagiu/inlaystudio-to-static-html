# static-site-gen — Copilot Skill

> Genera un sito HTML statico dai documenti prodotti dalla skill **ENGenius** (CONCEPT, ANALYSIS, TEST_SPEC, FP_SIZING, DESIGN, WBS, ACTIVITY) e dalla skill **IMPACT** (how, how-deepdive, what-process, what, enterprise).

---

## Installazione

```bash
git clone https://github.com/dobuonagiu/inlaystudio-to-static-html.git
cd inlaystudio-to-static-html
./install.sh
```

Lo script installa la skill in `~/.copilot/skills/static-site-gen/` e verifica i prerequisiti (Python 3.9+, pyyaml).

```bash
# Installazione in path custom
./install.sh /custom/path/skills
```

---

## Utilizzo

### Tramite Copilot CLI (consigliato)

Invoca la skill direttamente dal tuo progetto:

```
Usa la skill static-site-gen per generare il sito di documentazione.
```

L'agente raccoglie interattivamente la configurazione, valida i path, opzionalmente scarica i documenti da DocMind ed esegue il generatore.

### Esecuzione diretta

```bash
cd /path/al/tuo/progetto

# Generazione completa
python3 ~/.copilot/skills/static-site-gen/generate_site.py --config site_config.yaml

# Build incrementale (solo un progetto)
python3 ~/.copilot/skills/static-site-gen/generate_site.py \
    --config site_config.yaml \
    --project my-backend

# Con CSS custom
python3 ~/.copilot/skills/static-site-gen/generate_site.py \
    --config site_config.yaml \
    --css ./my_theme.css
```

---

## Configurazione

Copia `site_config.example.yaml` come `site_config.yaml` nella root del tuo progetto:

```yaml
site:
  title: "Portfolio Documentazione"
  description: "Documentazione ENGenius/IMPACT"
  output_dir: "./docs"
  css_file: null  # null = usa CSS integrato; path = CSS custom

projects:
  - id: "my-backend"
    name: "my-backend-service"
    label: "My Backend"
    short: "BE"
    path: "../my-backend-service"
    type: "backend"        # backend | frontend | bff | service | parent
    color: "backend"
    badge: "Backend"
    desc: "Backend API principale"
    stack: ["Java 21", "Spring Boot 3", "MongoDB"]
    docmind_project: null  # nome progetto DocMind per pull automatico

  - id: "portfolio"
    name: "portfolio-container"
    label: "Portfolio"
    short: "PF"
    path: "../portfolio-container"
    type: "parent"         # contiene docs enterprise (IMPACT enterprise)
    color: "legacy"
    badge: "Portfolio"
    desc: "Repository padre con docs enterprise"
    stack: []
```

---

## Documenti supportati

Il generatore si adatta dinamicamente a ciò che trova — non è necessario che ogni progetto abbia tutti i documenti.

| Skill | Tipo | Path scansionato |
|-------|------|-----------------|
| **IMPACT how** | Architettura (00–19) | `<project>/docs/*.md` |
| **IMPACT how-deepdive** | Deep Dive entry point | `<project>/docs/impact/how/deepdive/*.md` |
| **IMPACT what-process** | Processi di business | `<project>/docs/impact/how/processes/*.md` |
| **IMPACT what** | Use Cases da browser | `<project>/docs/impact/what/*.md` |
| **IMPACT enterprise** | Portfolio cross-project | `<parent>/_enterprise/*.md` |
| **ENGenius** (standard) | Artefatti forward-eng | `<project>/artifacts/*.md` |
| **ENGenius** (agile) | Epics, User Stories | `<project>/artifacts/01_ba.md`, `02_epics.md`, `04_user_stories.md` |
| **ENGenius TEST_SPEC** | Test Specification | `<project>/artifacts/test_spec/*.md` |

---

## Struttura output

```
<output_dir>/
├── index.html              # Home: panoramica portfolio + project cards
├── search.html             # Ricerca full-text (Lunr.js)
├── mongodb.html            # Relazioni MongoDB (condizionale)
├── assets/
│   ├── style.css           # CSS (default o custom)
│   ├── app.js              # JS (Mermaid, pan/zoom, ricerca, tema)
│   └── search-index.js     # Indice full-text pre-built
├── enterprise/             # Docs enterprise (condizionale)
│   └── *.html
├── requirements/           # Coverage requisiti (condizionale)
│   └── *.html
└── projects/
    └── <project-id>/
        ├── index.html      # Panoramica progetto
        ├── *.html          # IMPACT how docs (00–19)
        ├── artifacts/      # ENGenius artefatti
        ├── test_spec/      # Test Spec
        └── impact/
            ├── process/    # IMPACT what-process
            ├── deepdive/   # IMPACT how-deepdive
            └── usecase/    # IMPACT what
```

---

## CSS Personalizzato

Il CSS di default è in `assets/default.css`. Per usare un tema custom:

```yaml
# In site_config.yaml
site:
  css_file: ./my_dark_theme.css
```

```bash
# Oppure da CLI (override temporaneo)
python3 generate_site.py --config site_config.yaml --css ./my_theme.css
```

---

## Struttura skill

```
~/.copilot/skills/static-site-gen/
├── SKILL.md                  ← Istruzioni agente (flusso interattivo)
├── generate_site.py          ← Generatore HTML
└── assets/
    ├── default.css           ← CSS default (sostituibile)
    └── default.js            ← JS (Mermaid, Lunr, pan/zoom)
```

---

## Prerequisiti

| Prerequisito | Note |
|-------------|------|
| Python 3.9+ | `python3 --version` |
| pyyaml | `pip install pyyaml` (installato automaticamente da `install.sh`) |
| Copilot CLI | Per invocare la skill |
| Internet (opzionale) | CDN per Mermaid, svg-pan-zoom, Lunr.js |

---

## Tecnologie del sito generato

| Componente | Tecnologia | Versione |
|------------|-----------|---------|
| Diagrammi | mermaid.js | @11 (CDN) |
| Pan/Zoom | svg-pan-zoom | @3.6.1 (CDN) |
| Ricerca full-text | Lunr.js | @2.3.9 (CDN) |
| Tema dark/light | CSS custom properties | — |

---

## Aggiornare la skill

```bash
cd /path/to/inlaystudio-to-static-html
git pull
./install.sh
```

---

## Documentazione

Vedi [`SITE_PLAYBOOK.md`](./SITE_PLAYBOOK.md) per la documentazione completa con tutti i prompt di utilizzo.
