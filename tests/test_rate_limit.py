"""
Tests para rate limiting y protección contra brute force.
"""
import unittest
import time

import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.server.storage import Storage
from src.server.security import SecurityManager
from src.server.config import MAX_LOGIN_ATTEMPTS, RATE_LIMIT_WINDOW
from src.common.errors import RateLimitError


class TestRateLimiting(unittest.TestCase):
    """Tests de rate limiting."""
    
    def setUp(self):
        """Configura storage temporal."""
        import tempfile
        self.temp_db = Path(tempfile.mktemp(suffix=".db"))
        self.storage = Storage(self.temp_db)
        self.security = SecurityManager(self.storage)
    
    def tearDown(self):
        """Limpia archivos temporales."""
        if self.temp_db.exists():
            self.temp_db.unlink()
    
    def test_normal_login_allowed(self):
        """Test de que login normal es permitido."""
        username = "alice"
        ip = "192.168.1.100"
        
        # Registrar intento exitoso
        self.storage.record_login_attempt(username, ip, success=True)
        
        # No debería lanzar excepción
        try:
            self.security.check_rate_limit(username, ip)
        except RateLimitError:
            self.fail("Login normal no debería ser bloqueado")
    
    def test_multiple_failed_attempts_blocked(self):
        """Test de que múltiples intentos fallidos son bloqueados."""
        username = "alice"
        ip = "192.168.1.100"
        
        # Simular MAX_LOGIN_ATTEMPTS intentos fallidos
        for i in range(MAX_LOGIN_ATTEMPTS):
            self.storage.record_login_attempt(username, ip, success=False)
        
        # El siguiente intento debería ser bloqueado
        with self.assertRaises(RateLimitError) as ctx:
            self.security.check_rate_limit(username, ip)
        
        error_msg = str(ctx.exception)
        self.assertIn("Demasiados intentos", error_msg)
    
    def test_failed_count_accurate(self):
        """Test de que el contador de intentos fallidos es preciso."""
        username = "alice"
        ip = "192.168.1.100"
        
        # 3 intentos fallidos
        for _ in range(3):
            self.storage.record_login_attempt(username, ip, success=False)
        
        count = self.storage.get_failed_login_count(username, RATE_LIMIT_WINDOW)
        self.assertEqual(count, 3)
    
    def test_successful_login_resets_counter(self):
        """Test de que login exitoso resetea el contador."""
        username = "alice"
        ip = "192.168.1.100"
        
        # Intentos fallidos
        for _ in range(3):
            self.storage.record_login_attempt(username, ip, success=False)
        
        # Login exitoso
        self.storage.record_login_attempt(username, ip, success=True)
        self.security.reset_failed_attempts(username)
        
        # El siguiente intento debería estar permitido
        try:
            self.security.check_rate_limit(username, ip)
        except RateLimitError:
            self.fail("Contador debería haberse reseteado")
    
    def test_different_users_independent_limits(self):
        """Test de que usuarios diferentes tienen límites independientes."""
        ip = "192.168.1.100"
        
        # Alice: MAX_LOGIN_ATTEMPTS intentos fallidos
        for _ in range(MAX_LOGIN_ATTEMPTS):
            self.storage.record_login_attempt("alice", ip, success=False)
        
        # Alice debería estar bloqueada
        with self.assertRaises(RateLimitError):
            self.security.check_rate_limit("alice", ip)
        
        # Bob debería estar permitido
        try:
            self.security.check_rate_limit("bob", ip)
        except RateLimitError:
            self.fail("Bob no debería estar bloqueado")

    def test_backoff_increases_on_repeated_blocked_attempts(self):
        """El backoff debe crecer en bloqueos consecutivos (1s, 2s, 4s...)."""
        username = "alice"
        ip = "192.168.1.100"

        for _ in range(MAX_LOGIN_ATTEMPTS):
            self.storage.record_login_attempt(username, ip, success=False)

        backoffs = []
        for _ in range(3):
            with self.assertRaises(RateLimitError) as ctx:
                self.security.check_rate_limit(username, ip)
            backoffs.append(self._extract_backoff_seconds(str(ctx.exception)))

        self.assertEqual(backoffs, [1, 2, 4])

    @staticmethod
    def _extract_backoff_seconds(error_message: str) -> int:
        prefix = "Intente de nuevo en "
        suffix = " segundos."
        start = error_message.find(prefix)
        end = error_message.find(suffix)
        if start == -1 or end == -1:
            raise AssertionError(f"Formato de mensaje inesperado: {error_message}")
        value = error_message[start + len(prefix):end].strip()
        return int(value)


class TestBruteForceScenario(unittest.TestCase):
    """Tests de escenarios de brute force."""
    
    def setUp(self):
        """Configura storage temporal."""
        import tempfile
        self.temp_db = Path(tempfile.mktemp(suffix=".db"))
        self.storage = Storage(self.temp_db)
        self.security = SecurityManager(self.storage)
    
    def tearDown(self):
        """Limpia archivos temporales."""
        if self.temp_db.exists():
            self.temp_db.unlink()
    
    def test_brute_force_attack_simulation(self):
        """
        Simula un ataque de brute force.
        
        Escenario:
        1. Atacante intenta adivinar password de Alice
        2. Después de N intentos fallidos, es bloqueado
        """
        username = "alice"
        attacker_ip = "1.2.3.4"
        
        passwords_to_try = [
            "password123",
            "123456",
            "qwerty",
            "admin",
            "letmein",
            "trustno1"
        ]
        
        print(f"\n[ATACANTE] Intentando brute force en cuenta '{username}'...")
        
        for i, password in enumerate(passwords_to_try[:MAX_LOGIN_ATTEMPTS + 2], 1):
            try:
                # Verificar rate limit
                self.security.check_rate_limit(username, attacker_ip)
                
                # Simular intento fallido
                print(f"  Intento {i}: password='{password}' - FALLIDO")
                self.security.record_login_attempt(username, attacker_ip, success=False)
                
            except RateLimitError as e:
                print(f"  [OK] BLOQUEADO despues de {i-1} intentos")
                print(f"    Mensaje: {e}")
                return
        
        self.fail("El atacante no fue bloqueado despues de multiples intentos")


if __name__ == "__main__":
    unittest.main(verbosity=2)
