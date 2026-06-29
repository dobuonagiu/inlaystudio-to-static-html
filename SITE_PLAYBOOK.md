# Playbook — Generazione Sito Documentazione ENGenius/IMPACT

> **Procedura per la skill `static-site-gen` di GitHub Copilot CLI**
> Permette di generare, rigenerare e aggiornare il sito statico di documentazione tecnica
> a partire dai documenti prodotti dalle skill **ENGenius** (CONCEPT, ANALYSIS, TEST_SPEC,
> FP_SIZING, DESIGN, WBS, ACTIVITY) e **IMPACT** (how, how-deepdive, what-process, what, enterprise).

---

## Installazione della skill

```bash
# 1. Clona il repository
git clone https://github.com/<org>/inlaystudio-to-static-html

# 2. Installa la skill in ~/.copilot/skills/static-site-gen/
cd inlaystudio-to-static-html
./install.sh

# Oppure con path custom:
./install.sh /custom/path/skills
```

Lo script `install.sh` verifica Python 3.9+, installa pyyaml se mancante, copia i file
nella directory skill e verifica il funzionamento.

---

## Struttura dell'output

```
<output_dir>/
├── index.html                    # Home: panoramica portfolio + cards progetto
├── search.html                   # Ricerca full-text (Lunr.js)
├── mongodb.html                  # Relazioni MongoDB cross-project (condizionale)
├── assets/
│   ├── style.css                 # CSS (copiato da assets/default.css o CSS custom)
│   ├── app.js                    # JS (copiato da assets/default.js o JS custom)
│   └── search-index.js           # Indice pre-built per ricerca full-text
├── enterprise/                   # Docs enterprise cross-repo (condizionale)
│   ├── index.html
│   └── <stem>.html
├── requirements/                 # Coverage requisiti (condizionale)
│   └── <stem>.html
└── projects/
    └── <project-id>/
        ├── index.html            # Panoramica progetto
        ├── <stem>.html           # IMPACT how docs (00–19)
        ├── artifacts/
        │   └── <stem>.html       # ENGenius artefatti
        ├── test_spec/
        │   └── <stem>.html       # ENGenius test spec
        └── impact/
            ├── process/          # IMPACT what-process
            ├── deepdive/         # IMPACT how-deepdive
            └── usecase/          # IMPACT what
```

---

## Configurazione: `site_config.yaml`

Copia `site_config.example.yaml` come `site_config.yaml` nella root del progetto
da documentare e personalizza i campi.

```yaml
site:
  title: "Portfolio Documentazione"
  description: "Documentazione ENGenius/IMPACT"
  output_dir: "./docs"
  css_file: null           # null = usa CSS integrato della skill

projects:
  - id: "my-backend"
    name: "my-backend-service"
    label: "My Backend"
    short: "BE"
    path: "../my-backend-service"
    type: "backend"        # backend | frontend | bff | service | parent
    color: "backend"       # backend | frontend | bff | legacy | service
    badge: "Backend"
    desc: "Backend API principale"
    stack: ["Java 21", "Spring Boot 3"]
    docmind_project: null  # nome progetto DocMind per pull automatico

  - id: "portfolio"
    name: "portfolio-container"
    label: "Portfolio"
    short: "PF"
    path: "../portfolio-container"
    type: "parent"         # contiene docs enterprise
    color: "legacy"
    badge: "Portfolio"
    desc: "Repository padre con docs enterprise"
    stack: []
```

---

## PROMPT 1 — Generazione completa tramite skill

**Invoca la skill da Copilot CLI:**

```
Usa la skill static-site-gen per generare il sito di documentazione.
Il mio progetto è in /path/al/progetto e ho già un site_config.yaml.
```

La skill:
1. Cerca `site_config.yaml` nel CWD
2. Se non trovato: raccoglie la configurazione interattivamente
3. Valida i path e le dipendenze
4. Opzionalmente scarica docs da DocMind
5. Esegue `generate_site.py`
6. Verifica l'output e riporta il numero di pagine

---

## PROMPT 2 — Esecuzione diretta (senza skill)

```bash
cd /path/al/progetto

# Generazione completa
python3 ~/.copilot/skills/static-site-gen/generate_site.py --config site_config.yaml

# Build incrementale (solo un progetto)
python3 ~/.copilot/skills/static-site-gen/generate_site.py \
    --config site_config.yaml \
    --project my-backend

# Con CSS custom
python3 ~/.copilot/skills/static-site-gen/generate_site.py \
    --config site_config.yaml \
    --css /path/to/my_theme.css
```

---

## PROMPT 3 — Aggiunta di un nuovo repository

```
Aggiungi il progetto "my-new-service" al sito.
Path: ../my-new-service
Type: backend
Stack: Java 21, Spring Boot, Redis
```

La skill aggiunge la voce al `site_config.yaml` e rigenera il sito.

Oppure manualmente in `site_config.yaml`:
```yaml
  - id: "my-new-service"
    name: "my-new-service"
    label: "My New Service"
    short: "NS"
    path: "../my-new-service"
    type: "backend"
    color: "backend"
    badge: "Backend"
    desc: "Nuovo microservizio"
    stack: ["Java 21", "Spring Boot", "Redis"]
```

---

## PROMPT 4 — CSS personalizzato

La skill supporta CSS custom in due modi:

**1. Nel config** (permanente):
```yaml
site:
  css_file: ./my_custom_theme.css
```

**2. Da CLI** (override temporaneo):
```bash
python3 generate_site.py --config site_config.yaml --css ./dark_theme.css
```

Il file CSS viene copiato in `<output_dir>/assets/style.css`.
Il CSS di default si trova in `~/.copilot/skills/static-site-gen/assets/default.css`.

---

## PROMPT 5 — Aggiornamento sito dopo modifica docs

```
Uno o più file docs/ sono stati aggiornati.
Rigenera il sito per il progetto "my-backend".
```

La skill esegue:
```bash
python3 generate_site.py --config site_config.yaml --project my-backend
```

> **Nota:** il build incrementale (`--project`) non rigenera home, search e MongoDB page.
> Per aggiornare tutto, esegui senza `--project`.

---

## Documenti supportati

| Skill IMPACT | Tipo | Path scansionato |
|-------------|------|-----------------|
| `how` | Architettura 00–19 | `<project>/docs/*.md` |
| `how-deepdive` | Deep Dive entry point | `<project>/docs/impact/how/deepdive/*.md` |
| `what-process` | Processi di business | `<project>/docs/impact/how/processes/*.md` |
| `what` | Use cases da browser | `<project>/docs/impact/what/*.md` |
| `enterprise` | Portfolio cross-project | `<parent>/_enterprise/*.md` |

| Skill ENGenius | Tipo | Path scansionato |
|---------------|------|-----------------|
| CONCEPT/ANALYSIS/DESIGN/... | Artefatti | `<project>/artifacts/*.md` |
| TEST_SPEC | Test specification | `<project>/artifacts/test_spec/*.md` |

---

## Riferimenti tecnici

| Componente | Tecnologia | Versione |
|------------|-----------|---------|
| Mermaid rendering | mermaid.js | @11 (CDN) |
| Pan/Zoom diagrammi | svg-pan-zoom | @3.6.1 (CDN) |
| Ricerca full-text | Lunr.js | @2.3.9 (CDN) |
| Generator | Python | 3.9+ |
| Config format | YAML | via pyyaml |
| CSS theming | CSS custom properties | dark default + light toggle |

**Apertura locale del sito:**
```bash
# Linux/macOS
xdg-open docs/index.html
open docs/index.html

# Windows
start docs/index.html
```

**Il sito funziona completamente offline** tranne i CDN per Mermaid, svg-pan-zoom e Lunr.

---

*Generato il 2026-06-29 — ENGenius/IMPACT Static Site Generator*
