#!/usr/bin/env bash
set -euo pipefail

README_FILE="README.md"

if [[ ! -f "$README_FILE" ]]; then
  echo "Missing $README_FILE"
  exit 1
fi

required_patterns=(
  "pkg install ollama"
  "ollama serve"
  "ollama pull"
  "npm install -g openclaw@latest"
  "openclaw onboard --install-daemon"
)

for pattern in "${required_patterns[@]}"; do
  if ! grep -Fq "$pattern" "$README_FILE"; then
    echo "Missing required setup instruction: $pattern"
    exit 1
  fi
done

echo "README smoke test passed."
