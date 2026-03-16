"""Servidor TCP para transacciones financieras sobre TLS 1.3."""
import socket
import ssl
import threading
import logging
import json
import time
import signal
import sys
from typing import Optional

from .config import (
    SERVER_HOST,
    SERVER_PORT,
    LOG_DIR,
    LOG_LEVEL,
    LOG_TO_FILE,
    LOG_TO_CONSOLE,
    MAX_CONNECTIONS,
    TRANSPORT_MODE,
    TLS_CERT_FILE,
    TLS_KEY_FILE,
    TLS_CA_FILE,
    TLS_MIN_VERSION,
    TLS_ECDH_CURVE,
    TLS_ALLOWED_CIPHERS,
)
from .storage import Storage
from .security import SecurityManager
from .handlers import MessageHandler
from ..common.protocol import send_message, receive_message, create_error_response
from ..common.transport import normalize_transport_mode, create_server_ssl_context
from ..common.errors import ProtocolError, SecurityError


LOG_DIR.mkdir(parents=True, exist_ok=True)

handlers = []
if LOG_TO_CONSOLE:
    handlers.append(logging.StreamHandler())
if LOG_TO_FILE:
    handlers.append(logging.FileHandler(LOG_DIR / "server.log", encoding="utf-8"))

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=handlers,
)

logger = logging.getLogger(__name__)


class IntegrityServer:
    """Servidor TCP con TLS obligatorio."""

    def __init__(self, host: str = SERVER_HOST, port: int = SERVER_PORT):
        self.host = host
        self.port = port
        self.running = False
        self.server_socket: Optional[socket.socket] = None
        self.transport_mode = normalize_transport_mode(TRANSPORT_MODE)
        self.ssl_context: Optional[ssl.SSLContext] = None

        self.storage = Storage()
        self.security = SecurityManager(self.storage)
        self.handler = MessageHandler(self.storage, self.security)

        self.active_connections = 0
        self.connections_lock = threading.Lock()

        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        logger.info(f"Senal {signum} recibida, cerrando servidor...")
        self.stop()
        sys.exit(0)

    def start(self):
        """Inicia el servidor."""
        try:
            self.ssl_context = create_server_ssl_context(
                cert_file=TLS_CERT_FILE,
                key_file=TLS_KEY_FILE,
                ca_file=TLS_CA_FILE,
                min_version=TLS_MIN_VERSION,
                ecdh_curve=TLS_ECDH_CURVE,
            )

            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(MAX_CONNECTIONS)

            self.running = True
            logger.info(f"Transporte activo: {self.transport_mode}")
            logger.info(f"Curva ECDH activa: {TLS_ECDH_CURVE}")
            logger.info(f"Servidor iniciado en {self.host}:{self.port}")
            logger.info(f"Esperando conexiones (max: {MAX_CONNECTIONS})...")

            cleanup_thread = threading.Thread(target=self._periodic_cleanup, daemon=True)
            cleanup_thread.start()

            while self.running:
                try:
                    client_socket, client_address = self.server_socket.accept()

                    with self.connections_lock:
                        if self.active_connections >= MAX_CONNECTIONS:
                            logger.warning(
                                f"Conexion rechazada (maximo alcanzado): {client_address}"
                            )
                            client_socket.close()
                            continue

                        self.active_connections += 1

                    try:
                        client_socket = self.ssl_context.wrap_socket(
                            client_socket,
                            server_side=True,
                        )
                        negotiated = client_socket.cipher()
                        cipher_name = negotiated[0] if negotiated else None
                        if cipher_name not in TLS_ALLOWED_CIPHERS:
                            logger.warning(
                                "Conexion rechazada por cipher no permitido desde "
                                f"{client_address}: {cipher_name}"
                            )
                            with self.connections_lock:
                                self.active_connections -= 1
                            client_socket.close()
                            continue
                    except ssl.SSLError as e:
                        logger.warning(
                            f"Handshake TLS fallido desde {client_address}: {e}"
                        )
                        with self.connections_lock:
                            self.active_connections -= 1
                        client_socket.close()
                        continue

                    logger.info(
                        f"Nueva conexion desde {client_address} "
                        f"(activas: {self.active_connections})"
                    )

                    client_thread = threading.Thread(
                        target=self._handle_client,
                        args=(client_socket, client_address),
                        daemon=True,
                    )
                    client_thread.start()

                except Exception as e:
                    if self.running:
                        if self._is_expected_accept_error(e):
                            logger.debug(f"Error transitorio aceptando conexion: {e}")
                        else:
                            logger.error(f"Error aceptando conexion: {e}")

        except Exception as e:
            logger.error(f"Error iniciando servidor: {e}", exc_info=True)
            self.stop()

    def stop(self):
        """Detiene el servidor."""
        self.running = False
        if self.server_socket:
            try:
                self.server_socket.close()
            except Exception:
                pass
        logger.info("Servidor detenido")

    def _is_expected_accept_error(self, error: Exception) -> bool:
        """Identifica errores transitorios esperables durante handshakes fallidos."""
        winerror = getattr(error, "winerror", None)
        errno = getattr(error, "errno", None)
        message = str(error).lower()
        transient_codes = {10053, 10054, 104}

        return (
            winerror in transient_codes
            or errno in transient_codes
            or "10053" in message
            or "10054" in message
            or "connection reset by peer" in message
            or "software caused connection abort" in message
            or "established connection was aborted" in message
            or "anulada una conexion establecida" in message
            or "anulada una conexión establecida" in message
            or "interrupcion de una conexion existente" in message
            or "interrupción de una conexión existente" in message
        )

    def _periodic_cleanup(self):
        """Limpia datos antiguos periodicamente."""
        while self.running:
            time.sleep(60)
            try:
                self.security.cleanup_old_data()
            except Exception as e:
                logger.error(f"Error en limpieza periodica: {e}")

    def _handle_client(self, client_socket: socket.socket, client_address: tuple):
        """Maneja la comunicacion con un cliente."""
        client_ip = client_address[0]
        session_username: Optional[str] = None

        try:
            while self.running:
                try:
                    msg_dict = receive_message(client_socket, timeout=30.0)
                except ProtocolError as e:
                    error_text = str(e).lower()
                    if "cerrada" in error_text or "closed" in error_text:
                        break
                    if "timeout" in error_text:
                        # Timeout de inactividad: no enviar respuesta para no
                        # desincronizar el patron request/response del cliente.
                        logger.debug(f"Timeout de lectura desde {client_ip}: {e}")
                        continue
                    logger.warning(f"Error de protocolo desde {client_ip}: {e}")
                    error_resp = create_error_response("PROTOCOL_ERROR", str(e))
                    send_message(client_socket, error_resp)
                    continue

                try:
                    response = self._process_message(msg_dict, client_ip, session_username)

                    if (
                        msg_dict.get("type") == "LOGIN"
                        and response.get("success")
                        and "data" in response
                    ):
                        session_username = response["data"].get("username")

                    if msg_dict.get("type") == "LOGOUT":
                        session_username = None

                    send_message(client_socket, response)

                except Exception as e:
                    logger.error(f"Error procesando mensaje: {e}", exc_info=True)
                    error_resp = create_error_response(
                        "INTERNAL_ERROR", "Error interno del servidor"
                    )
                    send_message(client_socket, error_resp)

        except Exception as e:
            logger.error(f"Error en comunicacion con {client_ip}: {e}")

        finally:
            client_socket.close()
            with self.connections_lock:
                self.active_connections -= 1
            logger.info(f"Conexion cerrada: {client_ip} (activas: {self.active_connections})")

    def _process_message(
        self,
        msg_dict: dict,
        client_ip: str,
        session_username: Optional[str],
    ) -> dict:
        """Procesa un mensaje recibido y devuelve la respuesta."""
        msg_type = msg_dict.get("type")
        username = msg_dict.get("username", "")
        payload = msg_dict.get("payload", {})
        ts = msg_dict.get("ts", int(time.time() * 1000))

        logger.debug(f"Procesando {msg_type} de usuario '{username}' (IP: {client_ip})")

        try:
            if msg_type == "REGISTER":
                return self.handler.handle_register(username, payload, client_ip)

            if msg_type == "LOGIN":
                return self.handler.handle_login(username, payload, client_ip)

            if msg_type in ("MSG", "TX"):
                if not session_username or session_username != username:
                    logger.warning(
                        f"{msg_type} rechazada: usuario '{username}' sin sesion activa (IP: {client_ip})"
                    )
                    return create_error_response(
                        "AUTH_ERROR",
                        "Debe iniciar sesion antes de enviar mensajes",
                    )

                if msg_type == "TX":
                    raw_message = json.dumps(msg_dict, sort_keys=True)
                    return self.handler.handle_transaction(
                        username,
                        payload,
                        raw_message,
                        ts,
                    )

                return self.handler.handle_message(username, payload, ts)

            if msg_type == "HISTORY":
                if not session_username or session_username != username:
                    logger.warning(
                        f"HISTORY rechazada: usuario '{username}' sin sesion activa (IP: {client_ip})"
                    )
                    return create_error_response(
                        "AUTH_ERROR",
                        "Debe iniciar sesion antes de consultar historial",
                    )
                return self.handler.handle_history(username, payload)

            if msg_type == "LOGOUT":
                if not session_username or session_username != username:
                    logger.warning(
                        f"LOGOUT rechazado: usuario '{username}' sin sesion activa (IP: {client_ip})"
                    )
                    return create_error_response(
                        "AUTH_ERROR",
                        "No hay sesion activa para cerrar",
                    )
                return self.handler.handle_logout(username, payload)

            if msg_type == "PING":
                return self.handler.handle_ping(username)

            return create_error_response(
                "UNKNOWN_TYPE",
                f"Tipo de mensaje desconocido: {msg_type}",
            )

        except SecurityError as e:
            return create_error_response("SECURITY_ERROR", str(e))


def main():
    """Punto de entrada del servidor."""
    logger.info("=" * 60)
    logger.info("PAI2 - BYODSEC Road Warrior VPN SSL/TLS (Servidor)")
    logger.info("=" * 60)

    server = IntegrityServer()

    try:
        server.start()
    except KeyboardInterrupt:
        logger.info("Interrupcion de teclado recibida")
        server.stop()


if __name__ == "__main__":
    main()
