"""Tests para evitar desincronizacion por timeout de inactividad en servidor."""
import sys
import threading
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.common.errors import ProtocolError
from src.server.server import IntegrityServer


class _DummySocket:
    def __init__(self):
        self.closed = False

    def close(self):
        self.closed = True


class TestServerIdleTimeoutSync(unittest.TestCase):
    """Valida que timeout de lectura no genere respuestas no solicitadas."""

    def test_idle_timeout_does_not_send_protocol_error_response(self):
        server = IntegrityServer.__new__(IntegrityServer)
        server.running = True
        server.connections_lock = threading.Lock()
        server.active_connections = 1

        login_request = {
            "type": "LOGIN",
            "username": "alice",
            "payload": {"password": "x"},
            "ts": 1,
        }
        login_response = {
            "success": True,
            "message": "Login exitoso",
            "data": {"session_id": "s", "username": "alice"},
        }
        server._process_message = Mock(return_value=login_response)

        recv_events = [
            ProtocolError("Timeout esperando respuesta"),
            login_request,
            ProtocolError("Conexion cerrada por el peer"),
        ]

        def _fake_receive_message(*args, **kwargs):
            event = recv_events.pop(0)
            if isinstance(event, Exception):
                raise event
            return event

        sent_messages = []

        def _fake_send_message(_sock, message):
            sent_messages.append(message)

        socket_obj = _DummySocket()

        with patch("src.server.server.receive_message", side_effect=_fake_receive_message), patch(
            "src.server.server.send_message", side_effect=_fake_send_message
        ):
            server._handle_client(socket_obj, ("127.0.0.1", 5555))

        self.assertEqual(sent_messages, [login_response])
        server._process_message.assert_called_once_with(login_request, "127.0.0.1", None)
        self.assertTrue(socket_obj.closed)
        self.assertEqual(server.active_connections, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
