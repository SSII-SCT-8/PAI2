"""Tests basicos del lado cliente: creacion de mensajes y estado de autenticacion."""

import unittest

import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.client.api import ClientAPI


class TestCliente(unittest.TestCase):
    def setUp(self):
        self.client = ClientAPI(host="127.0.0.1", port=9999)

    def test_create_message_shape(self):
        msg = self.client._create_message("PING", "alice", {"x": 1})
        self.assertEqual(msg["type"], "PING")
        self.assertEqual(msg["username"], "alice")
        self.assertEqual(msg["payload"], {"x": 1})
        self.assertIn("ts", msg)
        self.assertNotIn("mac", msg)
        self.assertNotIn("nonce", msg)

    def test_send_tx_requires_auth(self):
        response = self.client.send_transaction("ES1", "ES2", "10")
        self.assertFalse(response.get("success"))
        self.assertIn("No autenticado", response.get("message"))

    def test_logout_without_session(self):
        response = self.client.logout()
        self.assertFalse(response.get("success"))
        self.assertIn("No hay sesion", response.get("message"))


if __name__ == "__main__":
    unittest.main()
