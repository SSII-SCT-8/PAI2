"""
Configuracion del servidor.
"""
import os
from pathlib import Path
try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - fallback defensivo
    load_dotenv = None

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = BASE_DIR / "data" / "server.db"
LOG_DIR = BASE_DIR / "logs"
CONFIG_DIR = BASE_DIR / "config"

if load_dotenv is not None:
    load_dotenv(BASE_DIR / ".env", override=False)

SERVER_HOST = os.getenv("SERVER_HOST", "127.0.0.1")
SERVER_PORT = int(os.getenv("SERVER_PORT", "9999"))
TRANSPORT_MODE = os.getenv("TRANSPORT_MODE", "TLS")

TLS_CERT_FILE = Path(os.getenv("TLS_CERT_FILE", str(CONFIG_DIR / "tls" / "server.crt")))
TLS_KEY_FILE = Path(os.getenv("TLS_KEY_FILE", str(CONFIG_DIR / "tls" / "server.key")))
TLS_CA_FILE = Path(os.getenv("TLS_CA_FILE", str(CONFIG_DIR / "tls" / "ca.crt")))
TLS_MIN_VERSION = os.getenv("TLS_MIN_VERSION", "1.3")
TLS_ECDH_CURVE = os.getenv("TLS_ECDH_CURVE", "prime256v1")
TLS_ALLOWED_CIPHERS = tuple(
    cipher.strip()
    for cipher in os.getenv(
        "TLS_ALLOWED_CIPHERS",
        "TLS_AES_256_GCM_SHA384,TLS_CHACHA20_POLY1305_SHA256,TLS_AES_128_GCM_SHA256",
    ).split(",")
    if cipher.strip()
)

MAX_LOGIN_ATTEMPTS = 5
RATE_LIMIT_WINDOW = 300       # 5 min
BACKOFF_BASE = 2              # 2^n segundos
SESSION_TIMEOUT = 3600        # 1 hora

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_TO_FILE = True
LOG_TO_CONSOLE = True

DB_TIMEOUT = 10.0
MAX_CONNECTIONS = int(os.getenv("MAX_CONNECTIONS", "300"))
