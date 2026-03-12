#!/usr/bin/env bash
set -euo pipefail

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TRANSPORT_MODE="TLS"

printf "\n======================================================================\n"
printf " PAI2 - BYODSEC Road Warrior VPN SSL/TLS (Servidor)\n"
printf "======================================================================\n"
printf "Iniciando servidor...\n\n"

if [[ ! -f "$BASE_DIR/src/server/server.py" ]]; then
  echo "Error: no se encontro src/server/server.py"
  exit 1
fi

if [[ ! -f "$BASE_DIR/data/server.db" ]]; then
  echo "Base de datos no encontrada. Inicializando..."
  python "$BASE_DIR/config/seed_database.py"
  echo
fi

TLS_CERT_FILE="${TLS_CERT_FILE:-config/tls/server.crt}"
TLS_KEY_FILE="${TLS_KEY_FILE:-config/tls/server.key}"
TLS_CA_FILE="${TLS_CA_FILE:-config/tls/ca.crt}"
TLS_MIN_VERSION="${TLS_MIN_VERSION:-1.3}"

printf "Iniciando servidor en puerto 9999...\n"
printf "Modo de transporte: %s\n" "$TRANSPORT_MODE"
printf "TLS cert: %s\n" "$TLS_CERT_FILE"
printf "TLS key:  %s\n" "$TLS_KEY_FILE"
printf "TLS ca:   %s\n" "$TLS_CA_FILE"
printf "TLS min:  %s\n\n" "$TLS_MIN_VERSION"
printf "Para detener el servidor: Ctrl+C\n"
printf "Logs: logs/server.log\n\n"

cd "$BASE_DIR"
python -m src.server.server
