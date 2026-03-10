"""Tests para funciones criptograficas vigentes."""
import unittest

import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.common.crypto import (
    hash_password,
    verify_password,
    SALT_SIZE,
    PBKDF2_ITERATIONS,
)


class TestCrypto(unittest.TestCase):
    """Tests de hashing de password."""

    def test_password_hashing(self):
        password = "MySecurePassword123!"

        pw_hash, salt = hash_password(password)

        self.assertEqual(len(pw_hash), 32)
        self.assertEqual(len(salt), SALT_SIZE)

        _, salt2 = hash_password(password)
        self.assertNotEqual(salt, salt2)

    def test_password_verification_correct(self):
        password = "MyPassword"
        pw_hash, salt = hash_password(password)

        self.assertTrue(verify_password(password, pw_hash, salt))

    def test_password_verification_incorrect(self):
        password = "MyPassword"
        wrong_password = "WrongPassword"
        pw_hash, salt = hash_password(password)

        self.assertFalse(verify_password(wrong_password, pw_hash, salt))

    def test_pbkdf2_iterations_are_hardened(self):
        self.assertGreaterEqual(PBKDF2_ITERATIONS, 120000)


if __name__ == "__main__":
    unittest.main(verbosity=2)
