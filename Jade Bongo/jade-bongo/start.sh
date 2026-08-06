#!/usr/bin/env bash
# ============================================================
# ⭐ Jade Bɔngɔ́ — Démarrage tout-en-un
#   ./start.sh           → installe si besoin + démarre sur le port 8030
#   PORT=9000 ./start.sh → autre port
#   JADE_PARENT_PIN=xxx ./start.sh → PIN parent personnalisé
# Arrêt : Ctrl+C
# ============================================================
set -euo pipefail

# --- Chemins ---------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/backend"
PORT="${PORT:-8030}"

echo "⭐ Jade Bɔngɔ́ — démarrage…"
echo "   Dossier : $BACKEND_DIR"

# --- Python -----------------------------------------------------------------
if ! command -v python3 >/dev/null 2>&1; then
  echo "❌ Python 3 est requis. Installe-le : https://www.python.org/downloads/"
  exit 1
fi

PY_MINOR="$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
echo "   Python  : $PY_MINOR"

# --- Choix de l'interpréteur : venv local > système déjà équipé > création --
VENV_PY="$BACKEND_DIR/.venv/bin/python"

pick_python() {
  if [ -x "$VENV_PY" ]; then
    echo "$VENV_PY"; return
  fi
  if python3 -c "import fastapi, uvicorn" >/dev/null 2>&1; then
    echo "$(command -v python3)"; return
  fi
  # Rien de prêt → environnement isolé propre (ne touche pas au système)
  echo "📦 Création de l'environnement isolé (.venv)…"
  python3 -m venv "$BACKEND_DIR/.venv"
  "$VENV_PY" -m pip install --quiet --upgrade pip
  echo "📦 Installation des dépendances…"
  "$VENV_PY" -m pip install --quiet -r "$BACKEND_DIR/requirements.txt"
  echo "$VENV_PY"
}

PY="$(pick_python)"
echo "   Moteur  : $("$PY" -c 'import fastapi, uvicorn; print("FastAPI", fastapi.__version__)' 2>/dev/null || echo "erreur deps")"

# --- Port déjà utilisé ? ----------------------------------------------------
if curl -s --max-time 2 "http://127.0.0.1:$PORT/api/health" >/dev/null 2>&1; then
  echo "⚠️  Le port $PORT répond déjà — Jade Bɔngɔ́ semble déjà démarré."
  echo "   🎮 App Jade       : http://localhost:$PORT/"
  echo "   👨‍👩‍👧 Espace Parents : http://localhost:$PORT/parent.html"
  echo "   🖥  Command Center : http://localhost:$PORT/command.html"
  exit 0
fi

# --- Démarrage ---------------------------------------------------------------
export JADE_PARENT_PIN="${JADE_PARENT_PIN:-0000}"
export JADE_PEPPER="${JADE_PEPPER:-dev-pepper-change-me}"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  🎮 App Jade        → http://localhost:$PORT/"
echo "  👨‍👩‍👧 Espace Parents  → http://localhost:$PORT/parent.html"
echo "  🖥  Command Center  → http://localhost:$PORT/command.html"
echo "  📚 API (docs)      → http://localhost:$PORT/docs"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
[ "$JADE_PARENT_PIN" = "0000" ] && echo "  ⚠️  PIN parent par défaut (0000) — change-le avec : JADE_PARENT_PIN=secret ./start.sh"
echo ""

cd "$BACKEND_DIR"
exec "$PY" -m uvicorn app.main:app --host 0.0.0.0 --port "$PORT"
