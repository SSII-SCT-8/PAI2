#!/usr/bin/env bash
set -euo pipefail

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TRANSPORT_MODE="TLS"
SERVER_HOST="${SERVER_HOST:-127.0.0.1}"
SERVER_PORT="${SERVER_PORT:-9999}"

printf "\n======================================================================\n"
printf " PAI2 - BYODSEC Road Warrior VPN SSL/TLS (Cliente)\n"
printf "======================================================================\n"
printf "Iniciando cliente...\n\n"

if [[ ! -f "$BASE_DIR/src/client/client.py" ]]; then
  echo "Error: no se encontro src/client/client.py"
  exit 1
fi

TLS_CA_FILE="${TLS_CA_FILE:-config/tls/ca.crt}"
TLS_SERVER_HOSTNAME="${TLS_SERVER_HOSTNAME:-$SERVER_HOST}"
TLS_MIN_VERSION="${TLS_MIN_VERSION:-1.3}"

printf "Conectando al servidor en %s:%s...\n" "$SERVER_HOST" "$SERVER_PORT"
printf "Modo de transporte: %s\n" "$TRANSPORT_MODE"
printf "TLS CA:          %s\n" "$TLS_CA_FILE"
printf "TLS hostname:    %s\n" "$TLS_SERVER_HOSTNAME"
printf "TLS min version: %s\n\n" "$TLS_MIN_VERSION"
printf "Usuarios de prueba:\n"
printf "  - alice / AliceSecure2024!\n"
printf "  - bob / BobPassword123#\n"
printf "  - admin / AdminPass2024$\n\n"

cd "$BASE_DIR"
python -m src.client.client
