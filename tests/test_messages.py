"""Tests de validacion y persistencia de mensajes PAI2."""

import unittest
import tempfile
from pathlib import Path

import sys
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.server.storage import Storage
from src.server.security import SecurityManager
from src.server.handlers import MessageHandler


class TestMessages(unittest.TestCase):
    def setUp(self):
        self.temp_db = Path(tempfile.mktemp(suffix=".db"))
        self.storage = Storage(self.temp_db)
        self.security = SecurityManager(self.storage)
        self.handler = MessageHandler(self.storage, self.security)

    def tearDown(self):
        if self.temp_db.exists():
            self.temp_db.unlink()

    def test_message_length_boundaries(self):
        ok_143 = self.handler.handle_message("alice", {"text": "a" * 143}, ts=1)
        ok_144 = self.handler.handle_message("alice", {"text": "b" * 144}, ts=2)
        bad_145 = self.handler.handle_message("alice", {"text": "c" * 145}, ts=3)

        self.assertTrue(ok_143["success"])
        self.assertTrue(ok_144["success"])
        self.assertFalse(bad_145["success"])
        self.assertEqual(bad_145.get("code"), "MSG_TOO_LONG")

    def test_empty_message_rejected(self):
        resp = self.handler.handle_message("alice", {"text": "   "}, ts=1)
        self.assertFalse(resp["success"])
        self.assertEqual(resp.get("code"), "EMPTY_MESSAGE")

    def test_history_returns_desc_and_counter(self):
        self.handler.handle_message("alice", {"text": "primero"}, ts=100)
        self.handler.handle_message("alice", {"text": "segundo"}, ts=200)

        history = self.handler.handle_history("alice", {"limit": 10})
        self.assertTrue(history["success"])
        self.assertEqual(history["data"]["total_messages"], 2)
        self.assertEqual(history["data"]["messages"][0]["message_text"], "segundo")
        self.assertEqual(history["data"]["messages"][1]["message_text"], "primero")


if __name__ == "__main__":
    unittest.main(verbosity=2)
