"""Tests de integracion de transporte TLS (A7)."""
import shutil
import socket
import subprocess
import sys
import threading
import time
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import src.client.api as api_module
import src.server.server as server_module
from src.server.storage import Storage as RealStorage


class TestTLSTransportIntegration(unittest.TestCase):
    """Valida escenarios reales de transporte seguro."""

    @classmethod
    def setUpClass(cls):
        cls.host = "127.0.0.1"
        cls.port = cls._pick_free_port()

        cls._temp_paths = []
        cls.valid_cert_dir = cls._create_cert_bundle("valid")
        cls.invalid_cert_dir = cls._create_cert_bundle("invalid")

        db_dir = project_root / "data" / "tls_test_server_db"
        shutil.rmtree(db_dir, ignore_errors=True)
        db_dir.mkdir(parents=True, exist_ok=True)
        cls._temp_paths.append(db_dir)
        cls.db_path = db_dir / "tls_server_test.db"

        cls._patchers = [
            patch.object(server_module, "TRANSPORT_MODE", "TLS"),
            patch.object(server_module, "TLS_MIN_VERSION", "1.3"),
            patch.object(server_module, "TLS_CERT_FILE", cls.valid_cert_dir / "server.crt"),
            patch.object(server_module, "TLS_KEY_FILE", cls.valid_cert_dir / "server.key"),
            patch.object(server_module, "TLS_CA_FILE", cls.valid_cert_dir / "ca.crt"),
            patch.object(server_module, "Storage", lambda: RealStorage(cls.db_path)),
        ]
        for patcher in cls._patchers:
            patcher.start()

        cls.server = server_module.IntegrityServer(host=cls.host, port=cls.port)
        cls.server_thread = threading.Thread(target=cls.server.start, daemon=True)
        cls.server_thread.start()

        cls._wait_for_tls_server_ready(
            host=cls.host,
            port=cls.port,
            ca_file=cls.valid_cert_dir / "ca.crt",
        )

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, "server"):
            cls.server.stop()
        if hasattr(cls, "server_thread"):
            cls.server_thread.join(timeout=2)

        for patcher in getattr(cls, "_patchers", []):
            patcher.stop()

        for path in getattr(cls, "_temp_paths", []):
            shutil.rmtree(path, ignore_errors=True)

    def test_tls_valid_connection(self):
        with patch.object(api_module, "TRANSPORT_MODE", "TLS"), \
             patch.object(api_module, "TLS_CA_FILE", self.valid_cert_dir / "ca.crt"), \
             patch.object(api_module, "TLS_MIN_VERSION", "1.3"), \
             patch.object(api_module, "TLS_SERVER_HOSTNAME", "localhost"):
            client = api_module.ClientAPI(host=self.host, port=self.port)
            self.assertTrue(client.connect())
            try:
                username = f"tls_valid_{uuid.uuid4().hex[:8]}"
                response = client.register(username, "SafePassword123!")
                self.assertTrue(response.get("success"), response)
            finally:
                client.disconnect()

    def test_tls_invalid_certificate_rejected(self):
        with patch.object(api_module, "TRANSPORT_MODE", "TLS"), \
             patch.object(api_module, "TLS_CA_FILE", self.invalid_cert_dir / "ca.crt"), \
             patch.object(api_module, "TLS_MIN_VERSION", "1.3"), \
             patch.object(api_module, "TLS_SERVER_HOSTNAME", "localhost"):
            client = api_module.ClientAPI(host=self.host, port=self.port)
            connected = client.connect()
            self.assertFalse(connected)
            self.assertEqual(client.last_connect_error_code, "TLS_HANDSHAKE_FAILED")

    def test_plain_client_against_tls_server_fails(self):
        with patch.object(api_module, "TRANSPORT_MODE", "PLAIN"):
            client = api_module.ClientAPI(host=self.host, port=self.port)
            self.assertTrue(client.connect())
            try:
                username = f"plain_fail_{uuid.uuid4().hex[:8]}"
                response = client.register(username, "SafePassword123!")
                self.assertFalse(response.get("success"))
                self.assertEqual(response.get("code"), "TLS_REQUIRED")
            finally:
                client.disconnect()

    @classmethod
    def _create_cert_bundle(cls, name: str) -> Path:
        out_dir = project_root / "data" / f"tls_test_{name}_bundle"
        shutil.rmtree(out_dir, ignore_errors=True)
        out_dir.mkdir(parents=True, exist_ok=True)
        cls._temp_paths.append(out_dir)

        cmd = [
            sys.executable,
            "scripts/generate_tls_certs.py",
            "--out-dir",
            str(out_dir),
            "--force",
        ]
        result = subprocess.run(
            cmd,
            cwd=project_root,
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(
                "Error generando certificados de prueba: "
                f"stdout={result.stdout!r} stderr={result.stderr!r}"
            )
        return out_dir

    @staticmethod
    def _pick_free_port() -> int:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(("127.0.0.1", 0))
            return sock.getsockname()[1]

    @staticmethod
    def _wait_for_tls_server_ready(host: str, port: int, ca_file: Path) -> None:
        import ssl

        deadline = time.time() + 10
        last_error = None
        while time.time() < deadline:
            try:
                context = ssl.create_default_context(cafile=str(ca_file))
                context.minimum_version = ssl.TLSVersion.TLSv1_3
                context.maximum_version = ssl.TLSVersion.TLSv1_3
                with socket.create_connection((host, port), timeout=1.0) as raw_sock:
                    with context.wrap_socket(raw_sock, server_hostname="localhost"):
                        return
            except Exception as exc:
                last_error = exc
                time.sleep(0.1)

        raise RuntimeError(f"No se pudo iniciar servidor TLS en {host}:{port}: {last_error}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
