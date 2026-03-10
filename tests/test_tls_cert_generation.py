"""Tests del generador de certificados TLS."""
import shutil
import subprocess
import sys
import unittest
import uuid
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives.asymmetric import ec, rsa

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class TestTLSCertGeneration(unittest.TestCase):
    """Valida el algoritmo de certificados generado por el script."""

    def setUp(self):
        self.out_dir = project_root / "data" / f"tls_cert_gen_{uuid.uuid4().hex[:12]}"
        shutil.rmtree(self.out_dir, ignore_errors=True)
        self.out_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        shutil.rmtree(self.out_dir, ignore_errors=True)

    def _run_generator(self, *extra_args: str) -> subprocess.CompletedProcess:
        cmd = [
            sys.executable,
            "scripts/generate_tls_certs.py",
            "--out-dir",
            str(self.out_dir),
            "--force",
            *extra_args,
        ]
        return subprocess.run(
            cmd,
            cwd=project_root,
            check=False,
            capture_output=True,
            text=True,
        )

    def test_default_generation_uses_ec_p256(self):
        result = self._run_generator()
        self.assertEqual(
            result.returncode,
            0,
            msg=f"stdout={result.stdout!r} stderr={result.stderr!r}",
        )

        server_cert = x509.load_pem_x509_certificate((self.out_dir / "server.crt").read_bytes())
        server_public_key = server_cert.public_key()

        self.assertIsInstance(server_public_key, ec.EllipticCurvePublicKey)
        self.assertEqual(server_public_key.curve.name, "secp256r1")

    def test_rsa_generation_is_available_for_compatibility(self):
        result = self._run_generator("--algorithm", "rsa")
        self.assertEqual(
            result.returncode,
            0,
            msg=f"stdout={result.stdout!r} stderr={result.stderr!r}",
        )

        server_cert = x509.load_pem_x509_certificate((self.out_dir / "server.crt").read_bytes())
        server_public_key = server_cert.public_key()

        self.assertIsInstance(server_public_key, rsa.RSAPublicKey)


if __name__ == "__main__":
    unittest.main(verbosity=2)
