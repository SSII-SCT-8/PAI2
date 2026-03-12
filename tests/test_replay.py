"""Tests para validar que el replay de aplicacion ya no existe (sin nonce)."""
import unittest

import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.client.api import ClientAPI


class TestReplayRemoved(unittest.TestCase):
    def test_client_messages_do_not_include_nonce(self):
        client = ClientAPI(host="127.0.0.1", port=9999)
        msg = client._create_message("MSG", "alice", {"text": "hola"})
        self.assertNotIn("nonce", msg)


if __name__ == "__main__":
    unittest.main(verbosity=2)
