"""Tests para configuracion de transporte TLS-only."""
import tempfile
import unittest
from pathlib import Path
import shutil

import sys
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.common.transport import (
    normalize_transport_mode,
    parse_tls_version,
    create_client_ssl_context,
    create_server_ssl_context,
)


class TestTransportTLS(unittest.TestCase):
    """Valida configuracion y endurecimiento de transporte."""

    def test_normalize_transport_mode(self):
        self.assertEqual(normalize_transport_mode("TLS"), "TLS")
        self.assertEqual(normalize_transport_mode(" tls "), "TLS")
        self.assertEqual(normalize_transport_mode(""), "TLS")

    def test_invalid_transport_mode(self):
        with self.assertRaises(ValueError):
            normalize_transport_mode("plain")

    def test_parse_tls_version(self):
        version = parse_tls_version("1.3")
        self.assertEqual(version.name, "TLSv1_3")

    def test_invalid_tls_version(self):
        with self.assertRaises(ValueError):
            parse_tls_version("1.2")

    def test_client_tls_requires_ca_file(self):
        with self.assertRaises(FileNotFoundError):
            create_client_ssl_context(
                ca_file=Path("missing-ca.pem"),
                min_version="1.3",
            )

    def test_server_tls_requires_cert_key_and_ca(self):
        temp_path = tempfile.mkdtemp(dir=project_root / "data")
        temp_dir = Path(temp_path)
        cert_file = temp_dir / "server.crt"
        key_file = temp_dir / "server.key"
        ca_file = temp_dir / "ca.crt"

        try:
            with self.assertRaises(FileNotFoundError):
                create_server_ssl_context(
                    cert_file=cert_file,
                    key_file=key_file,
                    ca_file=ca_file,
                    min_version="1.3",
                )
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
