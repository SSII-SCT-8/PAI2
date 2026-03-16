"""
Configuracion del cliente.
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
TRANSPORT_MODE = os.getenv("TRANSPORT_MODE", "TLS")

TLS_CA_FILE = Path(os.getenv("TLS_CA_FILE", str(BASE_DIR / "config" / "tls" / "ca.crt")))
TLS_MIN_VERSION = os.getenv("TLS_MIN_VERSION", "1.3")
TLS_SERVER_HOSTNAME = os.getenv("TLS_SERVER_HOSTNAME", SERVER_HOST)
TLS_ALLOWED_CIPHERS = tuple(
    cipher.strip()
    for cipher in os.getenv(
        "TLS_ALLOWED_CIPHERS",
        "TLS_AES_256_GCM_SHA384,TLS_CHACHA20_POLY1305_SHA256,TLS_AES_128_GCM_SHA256",
    ).split(",")
    if cipher.strip()
)

CONNECT_TIMEOUT = 10.0
MESSAGE_TIMEOUT = 30.0

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_TO_FILE = True
LOG_TO_CONSOLE = True

CLIENT_VERSION = "2.0.0"
