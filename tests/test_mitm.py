"""Tests para validar que la proteccion MITM ya no esta en capa de aplicacion (sin MAC)."""
import unittest

import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.client.api import ClientAPI
from src.common import crypto


class TestMITMRemoved(unittest.TestCase):
    def test_client_messages_do_not_include_mac(self):
        client = ClientAPI(host="127.0.0.1", port=9999)
        msg = client._create_message("TX", "alice", {"amount": "10"})
        self.assertNotIn("mac", msg)

    def test_hmac_helpers_removed_from_crypto_module(self):
        self.assertFalse(hasattr(crypto, "compute_hmac"))
        self.assertFalse(hasattr(crypto, "verify_hmac"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
