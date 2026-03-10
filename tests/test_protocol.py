"""Tests para funciones de protocolo de respuesta y framing."""
import unittest
import socket
import threading

import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.common.protocol import (
    send_message,
    receive_message,
    create_error_response,
    create_success_response,
)


class TestProtocol(unittest.TestCase):
    """Tests del protocolo de comunicacion."""

    def test_send_and_receive_message(self):
        left, right = socket.socketpair()
        try:
            expected = {"type": "PING", "payload": {"x": 1}}

            def sender():
                send_message(left, expected)

            thread = threading.Thread(target=sender)
            thread.start()
            received = receive_message(right, timeout=1.0)
            thread.join(timeout=1.0)

            self.assertEqual(received, expected)
        finally:
            left.close()
            right.close()

    def test_error_response(self):
        resp = create_error_response("TEST_CODE", "Test message")

        self.assertEqual(resp["type"], "ERROR")
        self.assertEqual(resp["code"], "TEST_CODE")
        self.assertEqual(resp["message"], "Test message")
        self.assertFalse(resp["success"])

    def test_success_response(self):
        resp = create_success_response("Success", {"key": "value"})

        self.assertEqual(resp["type"], "RESPONSE")
        self.assertEqual(resp["message"], "Success")
        self.assertTrue(resp["success"])
        self.assertEqual(resp["data"]["key"], "value")


if __name__ == "__main__":
    unittest.main()
