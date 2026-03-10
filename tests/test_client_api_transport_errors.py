"""Tests de respuestas de error y estados de conexion en ClientAPI."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import src.client.api as api_module
from src.common.errors import ProtocolError


class TestClientAPITransportErrors(unittest.TestCase):
    """Valida respuestas de errores de transporte."""

    @staticmethod
    def _tls_client() -> api_module.ClientAPI:
        with patch.object(api_module, "TRANSPORT_MODE", "TLS"):
            return api_module.ClientAPI(host="127.0.0.1", port=1)

    def test_not_connected_response_includes_last_code(self):
        client = self._tls_client()
        client.last_connect_error_code = "TLS_HANDSHAKE_FAILED"
        response = client._not_connected_response()
        self.assertFalse(response.get("success"))
        self.assertEqual(response.get("code"), "TLS_HANDSHAKE_FAILED")

    def test_transport_error_response_protocol_error(self):
        client = self._tls_client()
        response = client._transport_error_response(
            ProtocolError("Timeout esperando respuesta")
        )
        self.assertFalse(response.get("success"))
        self.assertIn("Timeout", response.get("message"))

    def test_transport_error_response_generic_error(self):
        client = self._tls_client()
        response = client._transport_error_response(OSError("Network is unreachable"))
        self.assertFalse(response.get("success"))
        self.assertIn("Network", response.get("message"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
