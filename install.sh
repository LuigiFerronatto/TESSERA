#!/usr/bin/env bash
# install.sh — instalador de um comando só para o Tessera.
#
# Uso:
#   ./install.sh                  # instalação padrão (core + mcp + llm), sem venv
#   ./install.sh --venv           # cria/usa um .venv local isolado antes de instalar
#   ./install.sh --venv .venv-x   # mesmo, com nome de venv customizado
#   ./install.sh --dev            # inclui extras[dev] (pytest) também
#   ./install.sh --minimal        # instala só o core (sem [mcp], sem [llm])
#   ./install.sh --no-doctor      # pula o `tessera doctor` de verificação no final
#   ./install.sh --quickstart     # ao final, roda `tessera quickstart` (dry-run) e mostra o plano
#
# Este script é seguro para rodar mais de uma vez (idempotente): reinstala
# em modo editável (`-e .`) e não apaga dados existentes em nenhum
# storage_dir de memórias.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# ---------------------------------------------------------------------------
# Cores (desligadas automaticamente se não for um TTY, ou se NO_COLOR/TESSERA_NO_COLOR estiver setado)
# ---------------------------------------------------------------------------
if [[ -t 1 && -z "${NO_COLOR:-}" && -z "${TESSERA_NO_COLOR:-}" ]]; then
    BOLD="\033[1m"; GREEN="\033[32m"; YELLOW="\033[33m"; RED="\033[31m"; CYAN="\033[36m"; RESET="\033[0m"
else
    BOLD=""; GREEN=""; YELLOW=""; RED=""; CYAN=""; RESET=""
fi

info()  { echo -e "${CYAN}==>${RESET} ${BOLD}$*${RESET}"; }
ok()    { echo -e "${GREEN}✓${RESET} $*"; }
warn()  { echo -e "${YELLOW}⚠${RESET} $*"; }
fail()  { echo -e "${RED}✗${RESET} $*" >&2; }

# ---------------------------------------------------------------------------
# Parse de flags
# ---------------------------------------------------------------------------
USE_VENV=0
VENV_NAME=".venv"
EXTRAS="mcp,llm"
NO_DOCTOR=0
RUN_QUICKSTART=0

while [[ $# -gt 0 ]]; do
    case "$1" in
        --venv)
            USE_VENV=1
            if [[ $# -gt 1 && "$2" != --* ]]; then VENV_NAME="$2"; shift; fi
            ;;
        --dev)
            EXTRAS="mcp,llm,dev"
            ;;
        --minimal)
            EXTRAS=""
            ;;
        --no-doctor)
            NO_DOCTOR=1
            ;;
        --quickstart)
            RUN_QUICKSTART=1
            ;;
        -h|--help)
            cat <<'EOF'
install.sh — instalador de um comando só para o Tessera.

Uso:
  ./install.sh                  # instalação padrão (core + mcp + llm), sem venv
  ./install.sh --venv           # cria/usa um .venv local isolado antes de instalar
  ./install.sh --venv .venv-x   # mesmo, com nome de venv customizado
  ./install.sh --dev            # inclui extras[dev] (pytest) também
  ./install.sh --minimal        # instala só o core (sem [mcp], sem [llm])
  ./install.sh --no-doctor      # pula o `tessera doctor` de verificação no final
  ./install.sh --quickstart     # ao final, roda `tessera quickstart` (dry-run) e mostra o plano

Idempotente: seguro rodar mais de uma vez (reinstala em modo editável,
nunca apaga dados de nenhum storage_dir de memórias já existente).
EOF
            exit 0
            ;;
        *)
            fail "Flag desconhecida: $1 (use --help)"
            exit 1
            ;;
    esac
    shift
done

# ---------------------------------------------------------------------------
# 1. Checar Python >= 3.9
# ---------------------------------------------------------------------------
info "Verificando versão do Python..."
PYTHON_BIN="${PYTHON_BIN:-python3}"
if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
    fail "python3 não encontrado no PATH. Instale Python >= 3.9 antes de continuar."
    exit 1
fi
PY_VERSION="$("$PYTHON_BIN" -c 'import sys; print("%d.%d" % sys.version_info[:2])')"
PY_MAJOR="${PY_VERSION%.*}"
PY_MINOR="${PY_VERSION#*.}"
if [[ "$PY_MAJOR" -lt 3 || ( "$PY_MAJOR" -eq 3 && "$PY_MINOR" -lt 9 ) ]]; then
    fail "Python $PY_VERSION encontrado, mas o Tessera requer >= 3.9."
    exit 1
fi
ok "Python $PY_VERSION OK ($PYTHON_BIN)"

# ---------------------------------------------------------------------------
# 2. (Opcional) criar/ativar venv
# ---------------------------------------------------------------------------
if [[ "$USE_VENV" -eq 1 ]]; then
    if [[ ! -d "$VENV_NAME" ]]; then
        info "Criando venv em ./$VENV_NAME..."
        "$PYTHON_BIN" -m venv "$VENV_NAME"
        ok "venv criado."
    else
        info "Reaproveitando venv existente ./$VENV_NAME"
    fi
    # shellcheck disable=SC1091
    source "$VENV_NAME/bin/activate"
    PYTHON_BIN="python3"
    ok "venv ativado: $(command -v python3)"
fi

# ---------------------------------------------------------------------------
# 3. Instalar o pacote (modo editável)
# ---------------------------------------------------------------------------
PIP_TARGET="."
if [[ -n "$EXTRAS" ]]; then
    PIP_TARGET=".[${EXTRAS}]"
fi

info "Instalando tessera em modo editável ($PIP_TARGET)..."
# Nota: alguns ambientes têm UV_INDEX_URL/pip.conf apontando para um mirror
# corporativo (ex: Nexus interno) que pode estar inacessível daqui — nesse
# caso passamos --index-url explícito para o PyPI público como fallback.
# (Isso NÃO altera nenhuma config global, só esta chamada.)
install_with_pypi_fallback() {
    if command -v uv >/dev/null 2>&1; then
        if ! uv pip install -e "$PIP_TARGET" 2>/tmp/tessera_install_uv_err.log; then
            warn "Instalação via uv falhou (possível mirror corporativo inacessível). Tentando com --index-url https://pypi.org/simple explícito..."
            uv pip install -e "$PIP_TARGET" --index-url https://pypi.org/simple
        fi
    else
        "$PYTHON_BIN" -m pip install --upgrade pip >/dev/null 2>&1 || true
        if ! "$PYTHON_BIN" -m pip install -e "$PIP_TARGET" 2>/tmp/tessera_install_pip_err.log; then
            warn "Instalação via pip falhou (possível mirror corporativo inacessível). Tentando com --index-url https://pypi.org/simple explícito..."
            "$PYTHON_BIN" -m pip install -e "$PIP_TARGET" --index-url https://pypi.org/simple
        fi
    fi
}
install_with_pypi_fallback
ok "Pacote instalado (extras: ${EXTRAS:-nenhum})."

# ---------------------------------------------------------------------------
# 4. Confirmar que os comandos ficaram disponíveis
# ---------------------------------------------------------------------------
if ! command -v tessera >/dev/null 2>&1; then
    fail "comando 'tessera' não apareceu no PATH após a instalação."
    if [[ "$USE_VENV" -eq 0 ]]; then
        warn "Se você instalou fora de um venv, confira se o diretório de scripts do usuário (ex: ~/.local/bin) está no PATH."
    fi
    exit 1
fi
ok "Comando 'tessera' disponível: $(command -v tessera)"
if command -v tessera-mcp >/dev/null 2>&1; then
    ok "Comando 'tessera-mcp' disponível: $(command -v tessera-mcp)"
fi

# ---------------------------------------------------------------------------
# 5. tessera doctor — smoke test pós-instalação
# ---------------------------------------------------------------------------
if [[ "$NO_DOCTOR" -eq 0 ]]; then
    info "Rodando 'tessera doctor' para validar a instalação..."
    if tessera doctor "$(mktemp -d)"; then
        ok "tessera doctor passou em todas as checagens obrigatórias."
    else
        warn "tessera doctor reportou alguma checagem obrigatória falhando (veja acima)."
        warn "A instalação do pacote em si funcionou; revise os itens marcados ✗."
    fi
else
    warn "Pulando 'tessera doctor' (--no-doctor)."
fi

# ---------------------------------------------------------------------------
# 6. (Opcional) tessera quickstart — dry-run
# ---------------------------------------------------------------------------
if [[ "$RUN_QUICKSTART" -eq 1 ]]; then
    info "Rodando 'tessera quickstart' (dry-run) a partir do diretório atual..."
    tessera quickstart --project-root "$(pwd)" || true
fi

echo
ok "Instalação concluída."
echo
echo -e "${BOLD}Próximos passos:${RESET}"
echo "  1. tessera quickstart --apply         # detecta seu projeto e cria o storage_dir de memórias"
echo "  2. tessera doctor <storage_dir>       # roda o smoke test completo na sua memória real"
echo "  3. tessera write <storage_dir> --id ... --type ... --episode start --content ...  # primeira nota"
echo "  4. Ver Tessera/docs/CHEATSHEET.md      # referência completa de CLI, MCP e API Python"
if [[ "$USE_VENV" -eq 1 ]]; then
    echo
    warn "Lembre de ativar o venv em novas sessões de shell: source $VENV_NAME/bin/activate"
fi
