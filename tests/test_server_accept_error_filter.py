"""Tests del filtro de errores transitorios en accept() del servidor."""
import sys
import unittest
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.server.server import IntegrityServer


class TestServerAcceptErrorFilter(unittest.TestCase):
    """Valida que el ruido conocido de TLS fallido no llegue como error."""

    @staticmethod
    def _server_with_mode(mode: str) -> IntegrityServer:
        server = IntegrityServer.__new__(IntegrityServer)
        server.transport_mode = mode
        return server

    def test_winerror_10053_in_message_is_expected_in_tls(self):
        server = self._server_with_mode("TLS")
        error = OSError(
            "Error aceptando conexion: [WinError 10053] "
            "Se anulo una conexion establecida por el software en su equipo host"
        )
        self.assertTrue(server._is_expected_accept_error(error))

    def test_same_error_is_not_expected_in_plain_mode(self):
        server = self._server_with_mode("PLAIN")
        error = OSError("Error aceptando conexion: [WinError 10053]")
        self.assertFalse(server._is_expected_accept_error(error))


if __name__ == "__main__":
    unittest.main(verbosity=2)
