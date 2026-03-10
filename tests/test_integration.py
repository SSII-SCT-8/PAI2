"""
Tests de integracion completos.
"""
import unittest
import tempfile
from pathlib import Path

import sys
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.server.storage import Storage
from src.server.security import SecurityManager
from src.server.handlers import MessageHandler
from src.common.crypto import verify_password


class TestIntegration(unittest.TestCase):
    """Tests de integracion end-to-end."""

    def setUp(self):
        self.temp_db = Path(tempfile.mktemp(suffix=".db"))
        self.storage = Storage(self.temp_db)
        self.security = SecurityManager(self.storage)
        self.handler = MessageHandler(self.storage, self.security)

    def tearDown(self):
        if self.temp_db.exists():
            self.temp_db.unlink()

    def test_full_user_lifecycle(self):
        """Registro -> login -> transaccion -> logout."""
        username = "alice"
        password = "SecurePass123!"
        client_ip = "127.0.0.1"

        resp = self.handler.handle_register(username, {"password": password}, client_ip)
        self.assertTrue(resp["success"])

        user = self.storage.get_user(username)
        self.assertIsNotNone(user)
        self.assertEqual(user["username"], username)
        self.assertTrue(verify_password(password, user["pw_hash"], user["pw_salt"]))

        resp = self.handler.handle_login(username, {"password": password}, client_ip)
        self.assertTrue(resp["success"])
        session_id = resp["data"]["session_id"]

        resp = self.handler.handle_transaction(
            username,
            {
                "from_account": "ES1111",
                "to_account": "ES2222",
                "amount": "500.00",
            },
            raw_message='{"test": "message"}',
            ts=1234567890,
        )
        self.assertTrue(resp["success"])
        tx_id = resp["data"]["transaction_id"]
        self.assertGreater(tx_id, 0)

        txs = self.storage.get_user_transactions(username)
        self.assertEqual(len(txs), 1)
        self.assertEqual(txs[0]["from_account"], "ES1111")

        resp = self.handler.handle_logout(username, {"session_id": session_id})
        self.assertTrue(resp["success"])

        session = self.storage.get_session(session_id)
        self.assertIsNone(session)

    def test_register_duplicate_user(self):
        username = "bob"
        password = "pass123"
        client_ip = "127.0.0.1"

        resp1 = self.handler.handle_register(username, {"password": password}, client_ip)
        self.assertTrue(resp1["success"])

        resp2 = self.handler.handle_register(username, {"password": password}, client_ip)
        self.assertFalse(resp2["success"])
        self.assertIn("ya existe", resp2["message"].lower())

    def test_login_wrong_password(self):
        username = "charlie"
        correct_password = "CorrectPass"
        wrong_password = "WrongPass"
        client_ip = "127.0.0.1"

        self.storage.create_user(username, correct_password)

        resp = self.handler.handle_login(username, {"password": wrong_password}, client_ip)
        self.assertFalse(resp["success"])
        self.assertIn("invalidas", resp["message"].lower())


if __name__ == "__main__":
    unittest.main(verbosity=2)
