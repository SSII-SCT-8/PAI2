"""Tests de clasificacion de errores de transporte en ClientAPI."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import src.client.api as api_module
from src.common.errors import ProtocolError


class TestClientAPITransportErrors(unittest.TestCase):
    """Valida mapeo de errores de transporte a respuestas de usuario."""

    @staticmethod
    def _plain_client() -> api_module.ClientAPI:
        with patch.object(api_module, "TRANSPORT_MODE", "PLAIN"):
            return api_module.ClientAPI(host="127.0.0.1", port=1)

    def test_timeout_protocol_error_is_not_tls_required(self):
        client = self._plain_client()
        response = client._transport_error_response(
            ProtocolError("Timeout esperando respuesta")
        )
        self.assertFalse(response.get("success"))
        self.assertNotIn("code", response)

    def test_connection_reset_protocol_error_is_tls_required(self):
        client = self._plain_client()
        response = client._transport_error_response(
            ProtocolError(
                "Error recibiendo mensaje: [WinError 10054] "
                "Se ha forzado la interrupcion de una conexion existente por el host remoto"
            )
        )
        self.assertFalse(response.get("success"))
        self.assertEqual(response.get("code"), "TLS_REQUIRED")

    def test_generic_oserror_is_not_tls_required(self):
        client = self._plain_client()
        response = client._transport_error_response(
            OSError(10051, "Network is unreachable")
        )
        self.assertFalse(response.get("success"))
        self.assertNotIn("code", response)

    def test_oserror_with_tls_signature_is_tls_required(self):
        client = self._plain_client()
        response = client._transport_error_response(
            OSError("SSL: WRONG_VERSION_NUMBER")
        )
        self.assertFalse(response.get("success"))
        self.assertEqual(response.get("code"), "TLS_REQUIRED")


if __name__ == "__main__":
    unittest.main(verbosity=2)
