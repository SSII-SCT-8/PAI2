"""Security tests: rate limit y sesiones."""

import unittest
import tempfile
from pathlib import Path

import sys
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.server.storage import Storage
from src.server.security import SecurityManager
from src.server.config import MAX_LOGIN_ATTEMPTS
from src.common.errors import RateLimitError


class TestSecurityFull(unittest.TestCase):
    def setUp(self):
        self.temp_db = Path(tempfile.mktemp(suffix=".db"))
        self.storage = Storage(self.temp_db)
        self.security = SecurityManager(self.storage)

    def tearDown(self):
        if self.temp_db.exists():
            self.temp_db.unlink()

    def test_login_brute_force(self):
        """Rate limit bloquea tras MAX_LOGIN_ATTEMPTS intentos."""
        for _ in range(MAX_LOGIN_ATTEMPTS):
            self.storage.record_login_attempt("alice", "1.2.3.4", False)
        with self.assertRaises(RateLimitError):
            self.security.check_rate_limit("alice", "1.2.3.4")

    def test_sql_injection_login_attempt_safe(self):
        """Caracteres de inyeccion SQL no rompen el storage."""
        evil = "'; DROP TABLE users;--"
        self.storage.record_login_attempt(evil, "127.0.0.1", False)
        count = self.storage.get_failed_login_count(evil, 600)
        self.assertEqual(count, 1)

    def test_session_validation_and_expire(self):
        """Sesion valida se mantiene y sesion expirada se elimina."""
        self.storage.create_session("alice", "session123")
        user = self.security.validate_session("session123")
        self.assertEqual(user, "alice")

        # Fuerza expiracion tocando last_seen
        with self.storage._get_connection() as conn:  # pylint: disable=protected-access
            cursor = conn.cursor()
            cursor.execute("UPDATE sessions SET last_seen = 0 WHERE session_id = ?", ("session123",))

        expired = self.security.validate_session("session123")
        self.assertIsNone(expired)


if __name__ == "__main__":
    unittest.main()
