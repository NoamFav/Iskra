#!/usr/bin/env bash
set -euo pipefail

PKG_NAME="autocommit"
CMDS=("ai_commit" "auto_commit" "pull_repos")
MIN_PY="3.9"

have() { command -v "$1" >/dev/null 2>&1; }

echo "==> Checking Python ${MIN_PY}+"
if ! have python3; then echo "ERROR: python3 not found"; exit 1; fi
python3 - <<PY || { echo "ERROR: Python ${MIN_PY}+ required"; exit 1; }
import sys
req=tuple(map(int,"${MIN_PY}".split(".")))
cur=sys.version_info[:2]
sys.exit(0 if cur>=req else 1)
PY

# ensure pip
python3 -m pip --version >/dev/null 2>&1 || python3 -m ensurepip --upgrade || true

USER_BASE="$(python3 -m site --user-base)"
USER_BIN="${USER_BASE}/bin"

echo "==> Installing ${PKG_NAME}"
if [ -n "${WHEEL_URL:-}" ]; then
  tmpwheel="$(mktemp -t ${PKG_NAME}.XXXXXX).whl"
  echo "Downloading wheel: $WHEEL_URL"
  if have curl; then curl -fsSL "$WHEEL_URL" -o "$tmpwheel"
  elif have wget; then wget -qO "$tmpwheel" "$WHEEL_URL"
  else echo "ERROR: need curl or wget"; exit 1
  fi
  python3 -m pip install --user --force-reinstall "$tmpwheel"
  rm -f "$tmpwheel"
else
  python3 -m pip install --user --upgrade "${PKG_NAME}"
fi

echo "==> Verifying commands"
missing=0
for c in "${CMDS[@]}"; do
  path="$(command -v "$c" || true)"
  if [ -z "$path" ] && [ -x "${USER_BIN}/${c}" ]; then
    path="${USER_BIN}/${c}"
  fi
  if [ -z "$path" ]; then
    echo "  - $c: NOT on PATH (installed to ${USER_BIN}/$c)"
    missing=1
  else
    echo "  - $c: $path"
    "$path" -h >/dev/null 2>&1 || { echo "     (warn) '$c -h' failed"; }
  fi
done

if [ $missing -eq 1 ]; then
  # choose a sensible profile file
  if [ -n "${ZSH_VERSION:-}" ]; then SHELL_RC="$HOME/.zprofile"
  elif [ -n "${BASH_VERSION:-}" ]; then SHELL_RC="$HOME/.bash_profile"
  else SHELL_RC="$HOME/.profile"
  fi
  echo
  echo "PATH fix needed. Add this to ${SHELL_RC}:"
  echo "    export PATH=\"${USER_BIN}:\$PATH\""
fi

echo
echo "==> (Optional) enable tab completion (argcomplete)"
if have register-python-argcomplete; then
  ACTIVATE_LINE='eval "$(register-python-argcomplete auto_commit)"; eval "$(register-python-argcomplete pull_repos)"'
  if [ -n "${ZSH_VERSION:-}" ]; then SHELL_RC="$HOME/.zshrc"; else SHELL_RC="$HOME/.bashrc"; fi
  if ! grep -qs 'register-python-argcomplete auto_commit' "$SHELL_RC" 2>/dev/null; then
    echo "$ACTIVATE_LINE" >> "$SHELL_RC"
    echo "  appended argcomplete activation to $SHELL_RC"
  else
    echo "  completion already configured"
  fi
else
  echo "  install with: python3 -m pip install --user argcomplete"
fi

echo
echo "==> Ollama (for AI messages)"
if have ollama; then
  echo "  ✔ ollama found. You can set OLLAMA_MODEL/OLLAMA_URL if desired."
else
  echo "  Note: ollama not found. Install https://ollama.com/ to use AI commit messages."
fi

echo
echo "==> Quick alias"
echo "Add this to your shell rc to commit only the current repo directory:"
echo '  alias q='\''auto_commit --only "${PWD##*/}"'\'''

echo
echo "✅ Done. Try:"
echo "  auto_commit --help"
echo "  pull_repos --help"
echo "  q   # (after adding the alias)"