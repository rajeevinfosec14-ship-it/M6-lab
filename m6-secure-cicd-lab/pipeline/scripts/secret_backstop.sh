#!/usr/bin/env bash
# secret_backstop.sh ROOT — a cheap regex backstop behind the real secret scanner. Exit 1 on any finding.
set -uo pipefail
ROOT="${1:-.}"
hits=0
scan() { # name  regex
  while IFS= read -r m; do
    [ -n "$m" ] && { echo "  [FINDING] $1: $m"; hits=$((hits+1)); }
  done < <(grep -rInE "$2" "$ROOT" \
            --exclude-dir=.git --exclude-dir=node_modules --exclude-dir=__pycache__ \
            --exclude=secret_backstop.sh --exclude=\*.md 2>/dev/null)
}
scan "AWS access key id"   'AKIA[0-9A-Z]{16}'
scan "private key block"   '-----BEGIN [A-Z ]*PRIVATE KEY-----'
scan "generic hardcoded secret" '(secret|token|passwd|password|api_key)[[:space:]]*=[[:space:]]*["'"'"'][^"'"'"']{8,}'

if [ "$hits" -eq 0 ]; then
  echo "  no secrets found — exit 0"; exit 0
fi
echo "  ${hits} finding(s) — exit 1"; exit 1
