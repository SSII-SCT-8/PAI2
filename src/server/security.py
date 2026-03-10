"""Seguridad: gestión de nonces, rate limiting, sesiones y validaciones."""
import time
import logging
from typing import Optional, Dict
from datetime import datetime

from .config import (
    TIMESTAMP_WINDOW,
    MAX_LOGIN_ATTEMPTS,
    RATE_LIMIT_WINDOW,
    BACKOFF_BASE,
    SESSION_TIMEOUT
)
from .storage import Storage
from ..common.errors import (
    ReplayAttackError,
    InvalidTimestampError,
    RateLimitError
)


logger = logging.getLogger(__name__)


class SecurityManager:
    """Gestiona la seguridad: nonces, rate limiting, sesiones."""
    
    def __init__(self, storage: Storage):
        self.storage = storage
        self._failed_attempts: Dict[str, int] = {}
    
    def validate_timestamp(self, ts: int) -> bool:
        """Valida que el timestamp esté dentro de la ventana permitida."""
        now_ms = int(time.time() * 1000)
        diff_seconds = abs(now_ms - ts) / 1000
        
        if diff_seconds > TIMESTAMP_WINDOW:
            raise InvalidTimestampError(
                f"Timestamp fuera de ventana permitida: {diff_seconds:.0f}s "
                f"(máximo: {TIMESTAMP_WINDOW}s)"
            )
        
        return True
    
    def check_and_store_nonce(self, username: str, nonce: str, ts: int) -> bool:
        """Verifica que el nonce no se haya usado antes y lo almacena."""
        if not self.storage.store_nonce(username, nonce, ts):
            logger.warning(
                f"REPLAY ATTACK detectado: usuario '{username}' "
                f"reutilizó nonce {nonce[:16]}..."
            )
            raise ReplayAttackError("Nonce ya utilizado (replay attack detectado)")
        
        return True
    
    def check_rate_limit(self, username: str, ip_address: str) -> None:
        """Verifica el rate limit de intentos de login."""
        failed_count = self.storage.get_failed_login_count(username, RATE_LIMIT_WINDOW)
        
        if failed_count >= MAX_LOGIN_ATTEMPTS:
            backoff_seconds = BACKOFF_BASE ** (failed_count - MAX_LOGIN_ATTEMPTS)

            # Registrar también el intento bloqueado para que el backoff
            # siga creciendo en reintentos consecutivos durante el bloqueo.
            self.storage.record_login_attempt(username, ip_address, success=False)
            
            logger.warning(
                f"RATE LIMIT: usuario '{username}' desde {ip_address} "
                f"bloqueado ({failed_count} intentos fallidos). "
                f"Backoff: {backoff_seconds}s"
            )
            
            raise RateLimitError(
                f"Demasiados intentos fallidos. "
                f"Intente de nuevo en {backoff_seconds} segundos."
            )
    
    def record_login_attempt(self, username: str, ip_address: str, success: bool) -> None:
        """Registra un intento de login."""
        self.storage.record_login_attempt(username, ip_address, success)
        
        if not success:
            self._failed_attempts[username] = self._failed_attempts.get(username, 0) + 1
    
    def reset_failed_attempts(self, username: str) -> None:
        """Resetea el contador de intentos fallidos tras login exitoso."""
        if username in self._failed_attempts:
            del self._failed_attempts[username]
        self.storage.clear_failed_login_attempts(username)
    
    def cleanup_old_data(self) -> None:
        """Limpia datos antiguos (nonces, intentos de login)."""
        self.storage.cleanup_old_nonces(max_age_seconds=TIMESTAMP_WINDOW * 2)
        self.storage.cleanup_old_login_attempts(max_age_seconds=RATE_LIMIT_WINDOW * 2)
        logger.debug("Limpieza de datos antiguos completada")
    
    def validate_session(self, session_id: str) -> Optional[str]:
        """Valida una sesión y retorna el username si es válida."""
        session = self.storage.get_session(session_id)
        if not session:
            return None
        # Verificar timeout
        now_ms = int(time.time() * 1000)
        age_seconds = (now_ms - session["last_seen"]) / 1000
        
        if age_seconds > SESSION_TIMEOUT:
            logger.info(f"Sesión expirada para usuario '{session['username']}'")
            self.storage.delete_session(session_id)
            return None
        
        self.storage.update_session_last_seen(session_id)
        
        return session["username"]
