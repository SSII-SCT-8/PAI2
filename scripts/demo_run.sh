#!/usr/bin/env bash
set -euo pipefail

SKIP_DB_RESET=0
GENERATE_CERTS=0

for arg in "$@"; do
  case "$arg" in
    --skip-db-reset) SKIP_DB_RESET=1 ;;
    --generate-certs) GENERATE_CERTS=1 ;;
    *) echo "Parametro no reconocido: $arg"; exit 1 ;;
  esac
done

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

printf "\n======================================================================\n"
printf " PAI2 - BYODSEC Road Warrior VPN SSL/TLS\n"
printf " Demo dinamica (modo: TLS)\n"
printf "======================================================================\n\n"

if [[ ! -d "$BASE_DIR/src" ]]; then
  echo "Error: no se encontro el directorio src/"
  echo "Ejecute este script desde el directorio scripts/"
  exit 1
fi

export SERVER_HOST="127.0.0.1"
export SERVER_PORT="9999"
export TRANSPORT_MODE="TLS"
export TLS_CERT_FILE="config/tls/server.crt"
export TLS_KEY_FILE="config/tls/server.key"
export TLS_CA_FILE="config/tls/ca.crt"
export TLS_SERVER_HOSTNAME="localhost"
export TLS_MIN_VERSION="1.3"

missing_tls=0
for tls_file in "$TLS_CERT_FILE" "$TLS_KEY_FILE" "$TLS_CA_FILE"; do
  if [[ ! -f "$BASE_DIR/$tls_file" ]]; then
    missing_tls=1
  fi
done

if [[ "$GENERATE_CERTS" -eq 1 || "$missing_tls" -eq 1 ]]; then
  echo "1. Generando certificados TLS..."
  python "$BASE_DIR/scripts/generate_tls_certs.py" --force
else
  echo "1. Certificados TLS detectados."
fi

if [[ "$SKIP_DB_RESET" -eq 0 ]]; then
  echo "2. Reiniciando base de datos..."
  if [[ -f "$BASE_DIR/data/server.db" ]]; then
    rm -f "$BASE_DIR/data/server.db"
    echo "   OK Base de datos eliminada"
  fi
  python "$BASE_DIR/config/seed_database.py"
else
  echo "2. SkipDbReset activo: se conserva la base de datos actual."
fi

echo
echo "3. Iniciando SERVIDOR en segundo plano..."
(
  cd "$BASE_DIR"
  python -m src.server.server
) &
SERVER_PID=$!

sleep 3

echo "4. Iniciando CLIENTE..."
cd "$BASE_DIR"
python -m src.client.client || true

kill "$SERVER_PID" >/dev/null 2>&1 || true
wait "$SERVER_PID" 2>/dev/null || true
