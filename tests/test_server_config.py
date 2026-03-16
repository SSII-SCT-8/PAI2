"""Tests para valores configurables del servidor."""
import importlib
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import src.server.config as server_config


class TestServerConfig(unittest.TestCase):
    """Valida defaults y overrides del modulo de configuracion."""

    def tearDown(self):
        importlib.reload(server_config)

    def test_default_max_connections_is_300(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("MAX_CONNECTIONS", None)
            cfg = importlib.reload(server_config)
            self.assertEqual(cfg.MAX_CONNECTIONS, 300)

    def test_max_connections_can_be_overridden(self):
        with patch.dict(os.environ, {"MAX_CONNECTIONS": "180"}, clear=False):
            cfg = importlib.reload(server_config)
            self.assertEqual(cfg.MAX_CONNECTIONS, 180)

    def test_tls_allowed_ciphers_has_three_defaults(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("TLS_ALLOWED_CIPHERS", None)
            cfg = importlib.reload(server_config)
            self.assertEqual(
                cfg.TLS_ALLOWED_CIPHERS,
                (
                    "TLS_AES_256_GCM_SHA384",
                    "TLS_CHACHA20_POLY1305_SHA256",
                    "TLS_AES_128_GCM_SHA256",
                ),
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
