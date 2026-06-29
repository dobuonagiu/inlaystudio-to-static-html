---
name: static-site-gen
description: >
  Genera un sito HTML statico dai documenti prodotti da ENGenius (CONCEPT, ANALYSIS,
  TEST_SPEC, FP_SIZING, DESIGN, WBS, ACTIVITY) e dalla skill IMPACT (how, how-deepdive,
  what-process, what, enterprise). Raccoglie interattivamente la configurazione (repos,
  path, sorgente docs), valida i prerequisiti, opzionalmente scarica documenti da DocMind,
  esegue generate_site.py e verifica l'output.
  Usare questa skill quando si vuole creare o aggiornare il sito di documentazione tecnica
  per un portfolio di progetti ENGenius/IMPACT.
---

# Static Site Generator — Skill

Questa skill genera un sito HTML statico dai documenti prodotti da **ENGenius** (pipeline
LEAP forward-engineering) e dalla skill **IMPACT** (reverse engineering).

---

## Documenti supportati

| Skill | Tipo | Path atteso |
|-------|------|-------------|
| IMPACT how | Architettura completa (00–19) | `<project>/docs/*.md` |
| IMPACT how-deepdive | Deep Dive entry point | `<project>/docs/impact/how/deepdive/*.md` |
| IMPACT what-process | Processi di business | `<project>/docs/impact/how/processes/*.md` |
| IMPACT what | Use cases da browser | `<project>/docs/impact/what/*.md` |
| IMPACT enterprise | Portfolio cross-project | `<parent>/_enterprise/*.md` |
| ENGenius | Artefatti forward-engineering | `<project>/artifacts/*.md` |
| ENGenius | Test Spec | `<project>/artifacts/test_spec/*.md` |

---

## Flusso agente

### STEP 1 — Verifica prerequisiti

1. Verifica che **Python 3.9+** sia disponibile:
   ```bash
   python3 --version
   ```
   Se non trovato, ferma e chiedi all'utente di installarlo.

2. Verifica che **pyyaml** sia installato:
   ```bash
   python3 -c "import yaml; print('ok')"
   ```
   Se mancante, installalo automaticamente:
   ```bash
   pip install pyyaml --quiet
   ```

3. Identifica lo **script generate_site.py**: si trova nella directory della skill stessa:
   ```
   ~/.copilot/skills/static-site-gen/generate_site.py
   ```
   Salva questo path come `SCRIPT_PATH` per i passi successivi.

---

### STEP 2 — Ricerca configurazione esistente

1. Controlla se nel **CWD** (working directory corrente) esiste un file `site_config.yaml`:
   ```bash
   ls site_config.yaml 2>/dev/null && echo "found" || echo "not found"
   ```

2. Se trovato: leggi il contenuto e vai al **STEP 3** (validazione).

3. Se **non trovato**: vai al **STEP 4** (raccolta interattiva).

---

### STEP 3 — Validazione configurazione esistente

Per ogni progetto nel config:
- Verifica che il `path` esista localmente
- Controlla quali sotto-cartelle di documenti esistono
- Segnala eventuali path non trovati ma non bloccare l'esecuzione

Chiedi all'utente:
> Il file `site_config.yaml` è stato trovato. Vuoi procedere con la configurazione attuale o vuoi modificarla?

Se vuole modificarla, vai al **STEP 4**.
Altrimenti vai al **STEP 5**.

---

### STEP 4 — Raccolta interattiva della configurazione

Se `site_config.yaml` non esiste, raccogliilo interattivamente.
**Non fare tutte le domande insieme.** Chiedi una alla volta.

#### 4a. Informazioni sito

Chiedi:
- **Titolo del sito** (es. "Portfolio Documentazione Tecnica")
- **Descrizione** breve (facoltativa, es. "Documentazione ENGenius/IMPACT — Team PNT")
- **Directory di output** (default: `./docs`, relativa al CWD)
- **CSS custom?** (default: usa il CSS integrato della skill) — se sì, chiedi il path

#### 4b. Elenco progetti

Chiedi all'utente di elencare i repository da includere.
Per ogni progetto, raccogli:

| Campo | Esempio | Note |
|-------|---------|------|
| `id` | `my-backend` | ID breve, usato negli URL (no spazi) |
| `name` | `my-backend-service` | Nome completo del repo |
| `label` | `My Backend` | Label per l'UI |
| `path` | `../my-backend-service` | Path al repository (relativo al CWD o assoluto) |
| `type` | `backend` | `backend`, `frontend`, `bff`, `service`, `parent` |
| `color` | `backend` | `backend`, `frontend`, `bff`, `legacy`, `service` |
| `badge` | `Backend` | Testo del badge nella card |
| `desc` | `API principale...` | Descrizione breve (1 riga) |
| `stack` | `["Java 21", "Spring"]` | Tecnologie (lista YAML) |

> **Nota**: il progetto di tipo `parent` è quello che contiene la documentazione enterprise
> (output di IMPACT enterprise, tipicamente in `_enterprise/`).

#### 4c. Sorgente documenti per progetto

Per ogni progetto che non ha una struttura `docs/` locale, chiedi:

> I documenti di `<nome_progetto>` sono disponibili:
> 1. In locale (path personalizzato)
> 2. Su DocMind (nome progetto DocMind)
> 3. Nessun documento ancora (salta questo progetto per ora)

Se sceglie **DocMind**: chiedi il nome del progetto DocMind e salva come `docmind_project`.

#### 4d. Generazione `site_config.yaml`

Una volta raccolte tutte le informazioni, genera il file `site_config.yaml` nel CWD
seguendo questo schema:

```yaml
site:
  title: "<TITOLO>"
  description: "<DESCRIZIONE>"
  output_dir: "<OUTPUT_DIR>"
  css_file: null  # o path al CSS custom

projects:
  - id: "<ID>"
    name: "<NAME>"
    label: "<LABEL>"
    short: "<SHORT>"
    path: "<PATH>"
    type: "<TYPE>"
    color: "<COLOR>"
    badge: "<BADGE>"
    desc: "<DESC>"
    stack: [<STACK>]
    docmind_project: null  # o "<DOCMIND_PROJECT_NAME>"
```

Mostra il contenuto generato e chiedi conferma prima di scrivere il file.

---

### STEP 5 — Pull documenti da DocMind (se configurato)

Per ogni progetto con `docmind_project` valorizzato:

1. Usa il tool MCP `docmind-listDocuments` per listare i documenti del progetto DocMind
2. Per ogni documento trovato, scaricane il contenuto con `docmind-getDocument`
3. Salva i documenti nella cartella appropriata:
   - Documenti IMPACT how → `<project>/docs/<stem>.md`
   - Artefatti ENGenius → `<project>/artifacts/<stem>.md`
   - Documenti enterprise → `<project>/_enterprise/<stem>.md`
4. Informa l'utente su quanti documenti sono stati scaricati

> **Nota**: se i tool DocMind non sono disponibili, segnalalo e procedi senza pull.

---

### STEP 6 — Esecuzione script

Esegui lo script con la configurazione:

```bash
python3 ~/.copilot/skills/static-site-gen/generate_site.py --config site_config.yaml
```

Se l'utente ha richiesto un build incrementale (es. "rigenera solo il progetto X"):
```bash
python3 ~/.copilot/skills/static-site-gen/generate_site.py --config site_config.yaml --project <ID>
```

Se è stato specificato un CSS custom da CLI:
```bash
python3 ~/.copilot/skills/static-site-gen/generate_site.py --config site_config.yaml --css path/to/custom.css
```

---

### STEP 7 — Verifica output

Dopo l'esecuzione:

1. Controlla che lo script abbia terminato con `✅ Done!`
2. Verifica che `<output_dir>/index.html` esista
3. Conta le pagine generate

Riporta all'utente:
```
✅ Sito generato con successo!
   📄 N pagine HTML in <output_dir>/
   🌐 Apri: file://<output_dir>/index.html
```

---

## Note operative

### CSS personalizzato
Il CSS predefinito è in `~/.copilot/skills/static-site-gen/assets/default.css`.
Per usare un CSS custom:
- Nel `site_config.yaml`: `css_file: ./my_theme.css`
- Da CLI: `python3 generate_site.py --css ./my_theme.css`

### Build incrementale
Per rigenare solo un progetto (utile dopo aggiornamenti parziali):
```bash
python3 ~/.copilot/skills/static-site-gen/generate_site.py --project <project-id>
```

### Aggiungere un progetto
1. Aggiungi la voce al `site_config.yaml`
2. Lancia il generatore (full rebuild)

### Aggiungere un nuovo tipo di documento
Lo script gestisce automaticamente i file non riconosciuti usando il nome del file come label.
Per aggiungere un'etichetta precisa, aggiungi la voce al dizionario `DOC_LABELS` in `generate_site.py`.

---

## Struttura skill

```
~/.copilot/skills/static-site-gen/
├── SKILL.md          ← questo file
├── generate_site.py  ← script generatore
└── assets/
    ├── default.css   ← CSS di default (sostituibile)
    └── default.js    ← JS di default (sostituibile)
```

Per aggiornare la skill:
```bash
cd /path/to/inlaystudio-to-static-html
./install.sh
```
