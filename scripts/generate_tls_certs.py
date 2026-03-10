"""Genera una CA local y un certificado de servidor para TLS 1.3.

Por defecto usa criptografia de curva eliptica (ECDSA + P-256).

Uso:
    python scripts/generate_tls_certs.py --force
"""
from __future__ import annotations

import argparse
import ipaddress
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Literal

try:
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import ec, rsa
    from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID
except ImportError as exc:
    raise SystemExit(
        "Falta dependencia 'cryptography'. Ejecuta: python -m pip install -r requirements.txt"
    ) from exc

SUPPORTED_ALGORITHMS = ("ec", "rsa")
_EC_CURVE_MAP: dict[str, type[ec.EllipticCurve]] = {
    "secp256r1": ec.SECP256R1,
    "prime256v1": ec.SECP256R1,
    "secp384r1": ec.SECP384R1,
    "secp521r1": ec.SECP521R1,
}


def _write_pem(path: Path, data: bytes, force: bool) -> None:
    if path.exists() and not force:
        raise FileExistsError(f"El archivo ya existe: {path}. Usa --force para sobrescribir.")
    path.write_bytes(data)


def _build_name(common_name: str, organization: str) -> x509.Name:
    return x509.Name(
        [
            x509.NameAttribute(NameOID.COUNTRY_NAME, "ES"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, organization),
            x509.NameAttribute(NameOID.COMMON_NAME, common_name),
        ]
    )


def _normalize_algorithm(algorithm: str) -> Literal["ec", "rsa"]:
    normalized = (algorithm or "ec").strip().lower()
    if normalized == "ec":
        return "ec"
    if normalized == "rsa":
        return "rsa"
    raise ValueError(
        f"--algorithm invalido: {algorithm}. Valores permitidos: {SUPPORTED_ALGORITHMS}"
    )


def _resolve_ec_curve(curve_name: str) -> ec.EllipticCurve:
    normalized = (curve_name or "secp256r1").strip().lower()
    curve_cls = _EC_CURVE_MAP.get(normalized)
    if curve_cls is None:
        allowed = ", ".join(sorted(_EC_CURVE_MAP.keys()))
        raise ValueError(
            f"--ec-curve invalida: {curve_name}. Valores permitidos: {allowed}"
        )
    return curve_cls()


def _generate_private_key(
    algorithm: Literal["ec", "rsa"],
    role: Literal["ca", "server"],
    ec_curve: ec.EllipticCurve,
) -> Any:
    if algorithm == "ec":
        return ec.generate_private_key(ec_curve)

    key_size = 4096 if role == "ca" else 3072
    return rsa.generate_private_key(public_exponent=65537, key_size=key_size)


def _generate_ca(
    organization: str,
    days: int,
    algorithm: Literal["ec", "rsa"],
    ec_curve: ec.EllipticCurve,
) -> tuple[Any, x509.Certificate]:
    now = datetime.now(timezone.utc)
    ca_key = _generate_private_key(algorithm, role="ca", ec_curve=ec_curve)
    ca_subject = _build_name("PAI2 Local Root CA", organization)
    builder = (
        x509.CertificateBuilder()
        .subject_name(ca_subject)
        .issuer_name(ca_subject)
        .public_key(ca_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=1))
        .not_valid_after(now + timedelta(days=days))
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
        .add_extension(
            x509.KeyUsage(
                digital_signature=True,
                key_encipherment=False,
                content_commitment=False,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=True,
                crl_sign=True,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .add_extension(x509.SubjectKeyIdentifier.from_public_key(ca_key.public_key()), critical=False)
    )
    ca_cert = builder.sign(private_key=ca_key, algorithm=hashes.SHA256())
    return ca_key, ca_cert


def _generate_server_cert(
    ca_key: Any,
    ca_cert: x509.Certificate,
    server_cn: str,
    days: int,
    algorithm: Literal["ec", "rsa"],
    ec_curve: ec.EllipticCurve,
) -> tuple[Any, x509.Certificate]:
    now = datetime.now(timezone.utc)
    server_key = _generate_private_key(algorithm, role="server", ec_curve=ec_curve)
    server_subject = _build_name(server_cn, "Universidad Publica")
    dns_names = {"localhost", server_cn}
    san = x509.SubjectAlternativeName(
        [*(x509.DNSName(name) for name in sorted(dns_names)), x509.IPAddress(ipaddress.ip_address("127.0.0.1"))]
    )
    builder = (
        x509.CertificateBuilder()
        .subject_name(server_subject)
        .issuer_name(ca_cert.subject)
        .public_key(server_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=1))
        .not_valid_after(now + timedelta(days=days))
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(san, critical=False)
        .add_extension(
            x509.KeyUsage(
                digital_signature=True,
                key_encipherment=(algorithm == "rsa"),
                content_commitment=False,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=False,
                crl_sign=False,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .add_extension(
            x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]),
            critical=False,
        )
        .add_extension(x509.SubjectKeyIdentifier.from_public_key(server_key.public_key()), critical=False)
        .add_extension(
            x509.AuthorityKeyIdentifier.from_issuer_public_key(ca_key.public_key()),
            critical=False,
        )
    )
    server_cert = builder.sign(private_key=ca_key, algorithm=hashes.SHA256())
    return server_key, server_cert


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Genera certificados TLS para PAI2")
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("config") / "tls",
        help="Directorio de salida (por defecto: config/tls)",
    )
    parser.add_argument(
        "--server-cn",
        default="localhost",
        help="Common Name del certificado de servidor (por defecto: localhost)",
    )
    parser.add_argument(
        "--organization",
        default="Universidad Publica",
        help="Organizacion para el sujeto de los certificados",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=825,
        help="Validez de los certificados en dias (por defecto: 825)",
    )
    parser.add_argument(
        "--algorithm",
        default="ec",
        help="Algoritmo para claves de CA/server: ec (default) o rsa",
    )
    parser.add_argument(
        "--ec-curve",
        default="secp256r1",
        help="Curva EC cuando --algorithm=ec (default: secp256r1)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Sobrescribe archivos existentes",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    try:
        algorithm = _normalize_algorithm(args.algorithm)
        ec_curve = _resolve_ec_curve(args.ec_curve)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    out_dir: Path = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    ca_key, ca_cert = _generate_ca(
        organization=args.organization,
        days=args.days,
        algorithm=algorithm,
        ec_curve=ec_curve,
    )
    server_key, server_cert = _generate_server_cert(
        ca_key=ca_key,
        ca_cert=ca_cert,
        server_cn=args.server_cn,
        days=args.days,
        algorithm=algorithm,
        ec_curve=ec_curve,
    )

    ca_key_path = out_dir / "ca.key"
    ca_cert_path = out_dir / "ca.crt"
    server_key_path = out_dir / "server.key"
    server_cert_path = out_dir / "server.crt"

    _write_pem(
        ca_key_path,
        ca_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        ),
        force=args.force,
    )
    _write_pem(
        ca_cert_path,
        ca_cert.public_bytes(serialization.Encoding.PEM),
        force=args.force,
    )
    _write_pem(
        server_key_path,
        server_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        ),
        force=args.force,
    )
    _write_pem(
        server_cert_path,
        server_cert.public_bytes(serialization.Encoding.PEM),
        force=args.force,
    )

    print("Certificados TLS generados:")
    print(f"  - CA cert:     {ca_cert_path}")
    print(f"  - CA key:      {ca_key_path}")
    print(f"  - Server cert: {server_cert_path}")
    print(f"  - Server key:  {server_key_path}")
    print(f"  - Algorithm:   {algorithm.upper()}")
    if algorithm == "ec":
        print(f"  - EC curve:    {ec_curve.name}")
    print("")
    print("SAN incluidos en server.crt: localhost, 127.0.0.1 y CN definido.")
    print("Usa TRANSPORT_MODE=TLS en cliente y servidor para activar TLS.")


if __name__ == "__main__":
    main()
