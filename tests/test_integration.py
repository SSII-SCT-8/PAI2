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
        """Registro -> login -> mensaje -> historial -> logout."""
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

        resp = self.handler.handle_message(
            username,
            {"text": "mensaje de prueba"},
            ts=1234567890,
        )
        self.assertTrue(resp["success"])
        msg_id = resp["data"]["message_id"]
        self.assertGreater(msg_id, 0)

        history = self.handler.handle_history(username, {"limit": 10})
        self.assertTrue(history["success"])
        self.assertEqual(history["data"]["total_messages"], 1)
        self.assertEqual(history["data"]["messages"][0]["message_text"], "mensaje de prueba")

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
