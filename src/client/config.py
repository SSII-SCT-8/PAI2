"""
Configuración del cliente.
"""
import os
from pathlib import Path
try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - fallback defensivo
    load_dotenv = None

BASE_DIR = Path(__file__).resolve().parent.parent.parent
LOG_DIR = BASE_DIR / "logs"

if load_dotenv is not None:
    load_dotenv(BASE_DIR / ".env", override=False)

SERVER_HOST = os.getenv("SERVER_HOST", "127.0.0.1")
SERVER_PORT = int(os.getenv("SERVER_PORT", "9999"))
TRANSPORT_MODE = os.getenv("TRANSPORT_MODE", "PLAIN")

TLS_CA_FILE = Path(os.getenv("TLS_CA_FILE", str(BASE_DIR / "config" / "tls" / "ca.crt")))
TLS_MIN_VERSION = os.getenv("TLS_MIN_VERSION", "1.3")
TLS_SERVER_HOSTNAME = os.getenv("TLS_SERVER_HOSTNAME", SERVER_HOST)

# Clave maestra (debe ser la misma que el servidor)
MASTER_KEY = os.getenv("MASTER_KEY")
if not MASTER_KEY:
    MASTER_KEY = "dev_master_key_256_bits_change_in_production_environment_please"

MASTER_KEY_BYTES = MASTER_KEY.encode('utf-8')[:32].ljust(32, b'\0')

CONNECT_TIMEOUT = 10.0
MESSAGE_TIMEOUT = 30.0

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_TO_FILE = True
LOG_TO_CONSOLE = True

CLIENT_VERSION = "1.0.0"
