"""
Handlers para los diferentes tipos de mensajes del protocolo.
"""
import logging
import secrets
import time
from typing import Dict, Any

from .storage import Storage
from .security import SecurityManager
from ..common.crypto import verify_password
from ..common.models import MESSAGE_MIN_LENGTH, MESSAGE_MAX_LENGTH
from ..common.errors import (
    AuthenticationError,
    UserAlreadyExistsError,
)


logger = logging.getLogger(__name__)


class MessageHandler:
    """Maneja los diferentes tipos de mensajes recibidos."""

    def __init__(self, storage: Storage, security: SecurityManager):
        self.storage = storage
        self.security = security

    def handle_register(
        self,
        username: str,
        payload: Dict[str, Any],
        client_ip: str,
    ) -> Dict[str, Any]:
        """Maneja el registro de un nuevo usuario."""
        try:
            password = payload.get("password")
            if not password:
                return {
                    "success": False,
                    "message": "Password requerido",
                }

            if self.storage.user_exists(username):
                logger.warning(
                    f"REGISTER fallido: usuario '{username}' ya existe (IP: {client_ip})"
                )
                raise UserAlreadyExistsError(f"El usuario '{username}' ya existe")

            self.storage.create_user(username, password)

            logger.info(f"Usuario '{username}' registrado exitosamente desde {client_ip}")

            return {
                "success": True,
                "message": f"Usuario '{username}' registrado exitosamente",
            }

        except UserAlreadyExistsError as e:
            return {
                "success": False,
                "message": str(e),
            }
        except Exception as e:
            logger.error(f"Error en REGISTER: {e}", exc_info=True)
            return {
                "success": False,
                "message": "Error interno del servidor",
            }

    def handle_login(
        self,
        username: str,
        payload: Dict[str, Any],
        client_ip: str,
    ) -> Dict[str, Any]:
        """Maneja el login de un usuario."""
        try:
            self.security.check_rate_limit(username, client_ip)

            password = payload.get("password")
            if not password:
                self.security.record_login_attempt(username, client_ip, False)
                return {
                    "success": False,
                    "message": "Password requerido",
                }

            user = self.storage.get_user(username)
            if not user:
                self.security.record_login_attempt(username, client_ip, False)
                logger.warning(
                    f"LOGIN fallido: usuario '{username}' no existe (IP: {client_ip})"
                )
                return {
                    "success": False,
                    "message": "Credenciales invalidas",
                }

            if not verify_password(password, user["pw_hash"], user["pw_salt"]):
                self.security.record_login_attempt(username, client_ip, False)
                logger.warning(
                    f"LOGIN fallido: password incorrecto para '{username}' (IP: {client_ip})"
                )
                return {
                    "success": False,
                    "message": "Credenciales invalidas",
                }

            session_id = secrets.token_urlsafe(32)
            self.storage.create_session(username, session_id)

            self.security.reset_failed_attempts(username)
            self.security.record_login_attempt(username, client_ip, True)

            logger.info(f"LOGIN exitoso: usuario '{username}' desde {client_ip}")

            return {
                "success": True,
                "message": "Login exitoso",
                "data": {
                    "session_id": session_id,
                    "username": username,
                },
            }

        except Exception as e:
            logger.error(f"Error en LOGIN: {e}", exc_info=True)
            return {
                "success": False,
                "message": str(e) if isinstance(e, (AuthenticationError, Exception)) else "Error interno",
            }

    def handle_transaction(
        self,
        username: str,
        payload: Dict[str, Any],
        raw_message: str,
        ts: int,
    ) -> Dict[str, Any]:
        """Compatibilidad legacy: transforma TX a MSG en texto."""
        try:
            from_account = payload.get("from_account")
            to_account = payload.get("to_account")
            amount = payload.get("amount")

            if not all([from_account, to_account, amount]):
                return {
                    "success": False,
                    "message": "Faltan campos: from_account, to_account, amount",
                }

            text = f"TX {from_account}->{to_account}: {amount}"
            return self.handle_message(
                username=username,
                payload={"text": text},
                ts=ts,
            )

        except Exception as e:
            logger.error(f"Error en TX: {e}", exc_info=True)
            return {
                "success": False,
                "message": "Error procesando mensaje legacy",
            }

    def handle_message(
        self,
        username: str,
        payload: Dict[str, Any],
        ts: int,
    ) -> Dict[str, Any]:
        """Maneja el envio de mensajes de texto (1..144)."""
        try:
            text = payload.get("text")

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

            message_id = self.storage.store_message(username, normalized, ts)
            total_messages = self.storage.count_user_messages(username)

            logger.info(f"MSG {message_id}: usuario '{username}'")

            return {
                "success": True,
                "message": "Mensaje enviado correctamente",
                "data": {
                    "message_id": message_id,
                    "text": normalized,
                    "ts": ts,
                    "total_messages": total_messages,
                },
            }
        except Exception as e:
            logger.error(f"Error en MSG: {e}", exc_info=True)
            return {
                "success": False,
                "message": "Error procesando mensaje",
            }

    def handle_history(
        self,
        username: str,
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Recupera historial y contador total de mensajes del usuario."""
        try:
            requested_limit = payload.get("limit", 50)

            if requested_limit is None:
                requested_limit = 50

            if not isinstance(requested_limit, int):
                return {
                    "success": False,
                    "code": "INVALID_HISTORY_LIMIT",
                    "message": "El limite de historial debe ser un entero",
                }

            if requested_limit < 1 or requested_limit > 500:
                return {
                    "success": False,
                    "code": "INVALID_HISTORY_LIMIT",
                    "message": "El limite de historial debe estar entre 1 y 500",
                }

            messages = self.storage.get_user_message_history(username, limit=requested_limit)
            total_messages = self.storage.count_user_messages(username)

            return {
                "success": True,
                "message": "Historial recuperado correctamente",
                "data": {
                    "messages": messages,
                    "count": len(messages),
                    "total_messages": total_messages,
                },
            }
        except Exception as e:
            logger.error(f"Error en HISTORY: {e}", exc_info=True)
            return {
                "success": False,
                "message": "Error recuperando historial",
            }

    def handle_logout(
        self,
        username: str,
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Maneja el logout de un usuario."""
        try:
            session_id = payload.get("session_id")
            if session_id:
                self.storage.delete_session(session_id)

            logger.info(f"LOGOUT: usuario '{username}'")

            return {
                "success": True,
                "message": "Logout exitoso",
            }

        except Exception as e:
            logger.error(f"Error en LOGOUT: {e}", exc_info=True)
            return {
                "success": True,
                "message": "Logout completado",
            }

    def handle_ping(self, username: str) -> Dict[str, Any]:
        """Maneja un mensaje PING (keep-alive)."""
        return {
            "success": True,
            "message": "PONG",
            "data": {
                "server_time": int(time.time() * 1000),
            },
        }
