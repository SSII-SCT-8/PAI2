"""Seguridad: rate limiting, sesiones y validaciones."""
import logging
from typing import Optional, Dict

from .config import (
    MAX_LOGIN_ATTEMPTS,
    RATE_LIMIT_WINDOW,
    BACKOFF_BASE,
    SESSION_TIMEOUT,
)
from .storage import Storage
from ..common.errors import RateLimitError


logger = logging.getLogger(__name__)


class SecurityManager:
    """Gestiona seguridad de aplicacion (sin MAC/nonce)."""

    def __init__(self, storage: Storage):
        self.storage = storage
        self._failed_attempts: Dict[str, int] = {}

    def check_rate_limit(self, username: str, ip_address: str) -> None:
        """Verifica el rate limit de intentos de login."""
        failed_count = self.storage.get_failed_login_count(username, RATE_LIMIT_WINDOW)

        if failed_count >= MAX_LOGIN_ATTEMPTS:
            backoff_seconds = BACKOFF_BASE ** (failed_count - MAX_LOGIN_ATTEMPTS)

            # Registrar tambien el intento bloqueado para que el backoff crezca.
            self.storage.record_login_attempt(username, ip_address, success=False)

            logger.warning(
                f"RATE LIMIT: usuario '{username}' desde {ip_address} "
                f"bloqueado ({failed_count} intentos fallidos). "
                f"Backoff: {backoff_seconds}s"
            )

            raise RateLimitError(
                "Demasiados intentos fallidos. "
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
        """Limpia datos antiguos de seguridad."""
        self.storage.cleanup_old_login_attempts(max_age_seconds=RATE_LIMIT_WINDOW * 2)
        logger.debug("Limpieza de datos antiguos completada")

    def validate_session(self, session_id: str) -> Optional[str]:
        """Valida una sesion y retorna el username si es valida."""
        session = self.storage.get_session(session_id)
        if not session:
            return None

        age_seconds = (self._now_ms() - session["last_seen"]) / 1000

        if age_seconds > SESSION_TIMEOUT:
            logger.info(f"Sesion expirada para usuario '{session['username']}'")
            self.storage.delete_session(session_id)
            return None

        self.storage.update_session_last_seen(session_id)
        return session["username"]

    @staticmethod
    def _now_ms() -> int:
        import time

        return int(time.time() * 1000)
