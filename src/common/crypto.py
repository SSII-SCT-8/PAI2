"""Funciones criptograficas para proteccion de credenciales."""
import hashlib
import secrets
from typing import Tuple


SALT_SIZE = 16          # 128 bits
PBKDF2_ITERATIONS = 150000  # OWASP >= 120,000 para SHA-256


def hash_password(password: str, salt: bytes = None) -> Tuple[bytes, bytes]:
    """Hash de password con PBKDF2-HMAC-SHA256. Retorna (hash, salt)."""
    if salt is None:
        salt = secrets.token_bytes(SALT_SIZE)

    pw_hash = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt,
        PBKDF2_ITERATIONS,
        dklen=32
    )

    return pw_hash, salt


def verify_password(password: str, pw_hash: bytes, salt: bytes) -> bool:
    """Verifica password en tiempo constante."""
    computed_hash, _ = hash_password(password, salt)
    return secrets.compare_digest(pw_hash, computed_hash)


def truncate_for_log(secret: str, visible_chars: int = 8) -> str:
    """Trunca secretos para logs."""
    if len(secret) <= visible_chars:
        return "***"
    return secret[:visible_chars] + "..." + f"[{len(secret)} chars total]"
