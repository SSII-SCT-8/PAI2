"""Utilidades de transporte TLS."""
from pathlib import Path
import ssl


SUPPORTED_TRANSPORT_MODES = {"TLS"}
_TLS_VERSION_MAP = {
    "1.3": ssl.TLSVersion.TLSv1_3,
}


def normalize_transport_mode(mode: str) -> str:
    """Normaliza y valida el modo de transporte."""
    normalized = (mode or "TLS").strip().upper()
    if normalized not in SUPPORTED_TRANSPORT_MODES:
        raise ValueError(
            f"TRANSPORT_MODE invalido: {mode}. "
            f"Valores permitidos: {sorted(SUPPORTED_TRANSPORT_MODES)}"
        )
    return normalized


def parse_tls_version(version: str) -> ssl.TLSVersion:
    """Convierte una version de texto a TLSVersion."""
    normalized = (version or "1.3").strip()
    if normalized not in _TLS_VERSION_MAP:
        raise ValueError(
            f"TLS_MIN_VERSION invalido: {version}. "
            f"Valores permitidos: {sorted(_TLS_VERSION_MAP.keys())}"
        )
    return _TLS_VERSION_MAP[normalized]


def create_server_ssl_context(
    cert_file: Path,
    key_file: Path,
    ca_file: Path,
    min_version: str,
) -> ssl.SSLContext:
    """Crea contexto TLS del servidor, forzando la version minima indicada."""
    if not cert_file.exists():
        raise FileNotFoundError(f"No existe TLS_CERT_FILE: {cert_file}")
    if not key_file.exists():
        raise FileNotFoundError(f"No existe TLS_KEY_FILE: {key_file}")
    if not ca_file.exists():
        raise FileNotFoundError(f"No existe TLS_CA_FILE: {ca_file}")

    tls_version = parse_tls_version(min_version)

    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.minimum_version = tls_version
    context.maximum_version = tls_version
    context.options |= ssl.OP_NO_COMPRESSION
    context.load_cert_chain(certfile=str(cert_file), keyfile=str(key_file))
    context.load_verify_locations(cafile=str(ca_file))
    return context


def create_client_ssl_context(ca_file: Path, min_version: str) -> ssl.SSLContext:
    """Crea contexto TLS del cliente con validacion de certificado de servidor."""
    if not ca_file.exists():
        raise FileNotFoundError(f"No existe TLS_CA_FILE: {ca_file}")

    tls_version = parse_tls_version(min_version)

    context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
    context.minimum_version = tls_version
    context.maximum_version = tls_version
    context.options |= ssl.OP_NO_COMPRESSION
    context.verify_mode = ssl.CERT_REQUIRED
    context.check_hostname = True
    context.load_verify_locations(cafile=str(ca_file))
    return context
