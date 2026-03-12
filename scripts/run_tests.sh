#!/usr/bin/env bash
set -euo pipefail

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

printf "\n======================================================================\n"
printf " PAI2 - Ejecutando Suite de Tests\n"
printf "======================================================================\n\n"

cd "$BASE_DIR"
python -m unittest discover -s tests -p "test_*.py" -v
