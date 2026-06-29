#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════
#  install.sh — Installa la skill static-site-gen
#
#  Uso:
#    ./install.sh                       # installa in ~/.copilot/skills/static-site-gen/
#    ./install.sh /custom/path/skills   # installa in /custom/path/skills/static-site-gen/
#
#  Prerequisiti:
#    - Python 3.9+
#    - pip (per installare pyyaml se mancante)
# ═══════════════════════════════════════════════════════════

set -e

SKILL_NAME="static-site-gen"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ── Destinazione ────────────────────────────────────────────
if [ -n "$1" ]; then
    DEST_BASE="$1"
else
    DEST_BASE="${HOME}/.copilot/skills"
fi
DEST="${DEST_BASE}/${SKILL_NAME}"

echo ""
echo "🔧  Installazione skill: ${SKILL_NAME}"
echo "    Sorgente : ${SCRIPT_DIR}"
echo "    Dest     : ${DEST}"
echo ""

# ── Verifica prerequisiti ────────────────────────────────────
echo "🔍  Verifica prerequisiti…"

# Python 3.9+
if ! command -v python3 &>/dev/null; then
    echo "❌  Python3 non trovato. Installa Python 3.9+ prima di procedere."
    exit 1
fi

PY_VER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
PY_MAJOR=$(python3 -c "import sys; print(sys.version_info.major)")
PY_MINOR=$(python3 -c "import sys; print(sys.version_info.minor)")

if [ "$PY_MAJOR" -lt 3 ] || { [ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 9 ]; }; then
    echo "❌  Python ${PY_VER} trovato, ma serve Python 3.9+."
    exit 1
fi
echo "  ✓ Python ${PY_VER}"

# pyyaml
if python3 -c "import yaml" &>/dev/null; then
    echo "  ✓ pyyaml già installato"
else
    echo "  ⚠️  pyyaml non trovato — installo…"
    pip install pyyaml --quiet
    echo "  ✓ pyyaml installato"
fi

# ── Crea directory destinazione ──────────────────────────────
mkdir -p "${DEST}/assets"

# ── Copia file ───────────────────────────────────────────────
echo ""
echo "📋  Copia file…"

# SKILL.md
cp "${SCRIPT_DIR}/SKILL.md" "${DEST}/SKILL.md"
echo "  ✓ SKILL.md"

# generate_site.py
cp "${SCRIPT_DIR}/generate_site.py" "${DEST}/generate_site.py"
echo "  ✓ generate_site.py"

# assets/
cp "${SCRIPT_DIR}/assets/default.css" "${DEST}/assets/default.css"
echo "  ✓ assets/default.css"

cp "${SCRIPT_DIR}/assets/default.js" "${DEST}/assets/default.js"
echo "  ✓ assets/default.js"

# example config (opzionale, utile come riferimento)
if [ -f "${SCRIPT_DIR}/site_config.example.yaml" ]; then
    cp "${SCRIPT_DIR}/site_config.example.yaml" "${DEST}/site_config.example.yaml"
    echo "  ✓ site_config.example.yaml"
fi

# ── Verifica ─────────────────────────────────────────────────
echo ""
echo "🔍  Verifica installazione…"
python3 "${DEST}/generate_site.py" --help > /dev/null 2>&1 && \
    echo "  ✓ generate_site.py funzionante" || \
    echo "  ⚠️  generate_site.py ha restituito un errore — controlla l'output manuale"

# ── Riepilogo ─────────────────────────────────────────────────
echo ""
echo "✅  Skill '${SKILL_NAME}' installata in:"
echo "    ${DEST}"
echo ""
echo "📌  Utilizzo:"
echo "    1. Invoca la skill da Copilot CLI: 'usa la skill static-site-gen'"
echo "    2. Oppure esegui direttamente:"
echo "       python3 ${DEST}/generate_site.py --config site_config.yaml"
echo ""
echo "📄  Configurazione di esempio:"
echo "    ${DEST}/site_config.example.yaml"
echo ""
