"""
API de comunicacion del cliente con el servidor.
"""
import socket
import ssl
import time
import logging
from typing import Dict, Any, Optional

from .config import (
    SERVER_HOST,
    SERVER_PORT,
    CONNECT_TIMEOUT,
    MESSAGE_TIMEOUT,
    TRANSPORT_MODE,
    TLS_CA_FILE,
    TLS_MIN_VERSION,
    TLS_SERVER_HOSTNAME,
    TLS_ALLOWED_CIPHERS,
)
from ..common.protocol import send_message, receive_message
from ..common.errors import ProtocolError
from ..common.transport import normalize_transport_mode, create_client_ssl_context
from ..common.models import MESSAGE_MIN_LENGTH, MESSAGE_MAX_LENGTH


logger = logging.getLogger(__name__)


class ClientAPI:
    """Cliente para comunicacion con el servidor sobre TLS 1.3."""

    def __init__(self, host: str = SERVER_HOST, port: int = SERVER_PORT):
        self.host = host
        self.port = port
        self.sock: Optional[socket.socket] = None
        self.connected = False
        self.transport_mode = normalize_transport_mode(TRANSPORT_MODE)
        self.last_connect_error_code: Optional[str] = None

        self.username: Optional[str] = None
        self.session_id: Optional[str] = None

    def connect(self) -> bool:
        """Conecta con el servidor usando TLS."""
        raw_socket: Optional[socket.socket] = None
        try:
            self.last_connect_error_code = None

            raw_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            raw_socket.settimeout(CONNECT_TIMEOUT)
            raw_socket.connect((self.host, self.port))

            ssl_context = create_client_ssl_context(
                ca_file=TLS_CA_FILE,
                min_version=TLS_MIN_VERSION,
            )
            self.sock = ssl_context.wrap_socket(
                raw_socket,
                server_hostname=TLS_SERVER_HOSTNAME,
            )
            negotiated = self.sock.cipher()
            cipher_name = negotiated[0] if negotiated else None
            if cipher_name not in TLS_ALLOWED_CIPHERS:
                self.last_connect_error_code = "TLS_CIPHER_NOT_ALLOWED"
                logger.error(
                    "Cipher TLS no permitido por politica local: "
                    f"{cipher_name}. Permitidos: {TLS_ALLOWED_CIPHERS}"
                )
                self.connected = False
                self.sock.close()
                self.sock = None
                return False

            self.connected = True
            logger.info(
                f"Conectado a {self.host}:{self.port} "
                f"(transporte={self.transport_mode})"
            )
            return True
        except ssl.SSLError as e:
            self.last_connect_error_code = "TLS_HANDSHAKE_FAILED"
            logger.error(f"Error TLS conectando: {e}")
            self.connected = False
            self.sock = None
            if raw_socket:
                raw_socket.close()
            return False
        except FileNotFoundError as e:
            self.last_connect_error_code = "TLS_CONFIG_ERROR"
            logger.error(f"Error de configuracion TLS: {e}")
            self.connected = False
            self.sock = None
            if raw_socket:
                raw_socket.close()
            return False
        except ValueError as e:
            self.last_connect_error_code = "TLS_CONFIG_ERROR"
            logger.error(f"Error de configuracion de transporte: {e}")
            self.connected = False
            self.sock = None
            if raw_socket:
                raw_socket.close()
            return False
        except Exception as e:
            logger.error(f"Error conectando: {e}")
            self.connected = False
            self.sock = None
            if raw_socket:
                raw_socket.close()
            return False

    def disconnect(self):
        """Desconecta del servidor."""
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass
        self.connected = False
        self.username = None
        self.session_id = None
        logger.info("Desconectado del servidor")

    def _not_connected_response(self) -> Dict[str, Any]:
        """Respuesta estandar cuando no hay conexion activa."""
        response: Dict[str, Any] = {
            "success": False,
            "message": "No conectado al servidor",
        }
        if self.last_connect_error_code:
            response["code"] = self.last_connect_error_code
        return response

    @staticmethod
    def _transport_error_response(error: Exception) -> Dict[str, Any]:
        """Normaliza errores de transporte para respuestas al usuario."""
        if isinstance(error, ProtocolError):
            return {"success": False, "message": str(error)}
        return {"success": False, "message": str(error)}

    @staticmethod
    def _create_message(
        msg_type: str,
        username: str,
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Crea un mensaje de aplicacion."""
        return {
            "type": msg_type,
            "ts": int(time.time() * 1000),
            "username": username,
            "payload": payload,
        }

    def register(self, username: str, password: str) -> Dict[str, Any]:
        """Registra un nuevo usuario."""
        if not self.connected:
            return self._not_connected_response()

        msg = self._create_message("REGISTER", username, {"password": password})

        try:
            send_message(self.sock, msg)
            response = receive_message(self.sock, timeout=MESSAGE_TIMEOUT)

            if response.get("success"):
                logger.info(f"Usuario '{username}' registrado exitosamente")

            return response

        except Exception as e:
            logger.error(f"Error en REGISTER: {e}")
            return self._transport_error_response(e)

    def login(self, username: str, password: str) -> Dict[str, Any]:
        """Inicia sesion."""
        if not self.connected:
            return self._not_connected_response()

        msg = self._create_message("LOGIN", username, {"password": password})

        try:
            send_message(self.sock, msg)
            response = receive_message(self.sock, timeout=MESSAGE_TIMEOUT)

            if response.get("success"):
                data = response.get("data", {})
                self.session_id = data.get("session_id")
                self.username = username
                logger.info(f"Login exitoso: usuario '{username}'")

            return response

        except Exception as e:
            logger.error(f"Error en LOGIN: {e}")
            return self._transport_error_response(e)

    def send_transaction(
        self,
        from_account: str,
        to_account: str,
        amount: str,
    ) -> Dict[str, Any]:
        """Compatibilidad legacy: encapsula una TX como mensaje de texto."""
        legacy_text = f"TX {from_account}->{to_account}: {amount}"
        return self.send_message_text(legacy_text)

    def send_message_text(self, text: str) -> Dict[str, Any]:
        """Envia un mensaje de texto (1..144 caracteres)."""
        if not self.username or not self.session_id:
            return {"success": False, "message": "No autenticado"}

        if not isinstance(text, str):
            return {
                "success": False,
                "code": "EMPTY_MESSAGE",
                "message": "El mensaje debe ser texto",
            }

        normalized = text.strip()
        if len(normalized) < MESSAGE_MIN_LENGTH:
            return {
                "success": False,
                "code": "EMPTY_MESSAGE",
                "message": "El mensaje no puede estar vacio",
            }
        if len(normalized) > MESSAGE_MAX_LENGTH:
            return {
                "success": False,
                "code": "MSG_TOO_LONG",
                "message": f"El mensaje no puede superar {MESSAGE_MAX_LENGTH} caracteres",
            }

        msg = self._create_message(
            "MSG",
            self.username,
            {
                "text": normalized,
            },
        )

        try:
            send_message(self.sock, msg)
            response = receive_message(self.sock, timeout=MESSAGE_TIMEOUT)

            if response.get("success"):
                logger.info(f"Mensaje enviado por '{self.username}'")

            return response

        except Exception as e:
            logger.error(f"Error en MSG: {e}")
            return self._transport_error_response(e)

    def get_history(self, limit: Optional[int] = None) -> Dict[str, Any]:
        """Recupera historial de mensajes del usuario autenticado."""
        if not self.username or not self.session_id:
            return {"success": False, "message": "No autenticado"}

        payload: Dict[str, Any] = {}
        if limit is not None:
            payload["limit"] = limit

        msg = self._create_message("HISTORY", self.username, payload)

        try:
            send_message(self.sock, msg)
            return receive_message(self.sock, timeout=MESSAGE_TIMEOUT)
        except Exception as e:
            logger.error(f"Error en HISTORY: {e}")
            return self._transport_error_response(e)

    def logout(self) -> Dict[str, Any]:
        """Cierra sesion."""
        if not self.username or not self.session_id:
            return {"success": False, "message": "No hay sesion activa"}

        msg = self._create_message(
            "LOGOUT",
            self.username,
            {"session_id": self.session_id},
        )

        try:
            send_message(self.sock, msg)
            response = receive_message(self.sock, timeout=MESSAGE_TIMEOUT)

            logger.info("Logout exitoso")

            self.session_id = None
            self.username = None

            return response

        except Exception as e:
            logger.error(f"Error en LOGOUT: {e}")
            return self._transport_error_response(e)
