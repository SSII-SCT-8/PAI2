"""
API de comunicación del cliente con el servidor.
"""
import socket
import ssl
import time
import logging
from typing import Dict, Any, Optional, Set

from .config import (
    SERVER_HOST,
    SERVER_PORT,
    CONNECT_TIMEOUT,
    MESSAGE_TIMEOUT,
    MASTER_KEY_BYTES,
    TRANSPORT_MODE,
    TLS_CA_FILE,
    TLS_MIN_VERSION,
    TLS_SERVER_HOSTNAME,
)
from ..common.protocol import (
    send_message,
    receive_message,
    canonicalize_message
)
from ..common.crypto import (
    generate_nonce,
    compute_hmac,
    derive_user_key
)
from ..common.models import Message
from ..common.errors import ProtocolError
from ..common.transport import normalize_transport_mode, create_client_ssl_context


logger = logging.getLogger(__name__)


class ClientAPI:
    """Cliente para comunicación con el servidor de integridad."""
    
    def __init__(self, host: str = SERVER_HOST, port: int = SERVER_PORT):
        self.host = host
        self.port = port
        self.sock: Optional[socket.socket] = None
        self.connected = False
        self.transport_mode = normalize_transport_mode(TRANSPORT_MODE)
        self.last_connect_error_code: Optional[str] = None
        
        self.username: Optional[str] = None
        self.session_id: Optional[str] = None
        self.user_key: Optional[bytes] = None
        self.user_key_salt: Optional[bytes] = None
        
        self._used_nonces: Set[str] = set()
    
    def connect(self) -> bool:
        """Conecta con el servidor."""
        raw_socket: Optional[socket.socket] = None
        try:
            self.last_connect_error_code = None

            raw_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            raw_socket.settimeout(CONNECT_TIMEOUT)
            raw_socket.connect((self.host, self.port))

            if self.transport_mode == "TLS":
                ssl_context = create_client_ssl_context(
                    ca_file=TLS_CA_FILE,
                    min_version=TLS_MIN_VERSION,
                )
                self.sock = ssl_context.wrap_socket(
                    raw_socket,
                    server_hostname=TLS_SERVER_HOSTNAME,
                )
            else:
                self.sock = raw_socket

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
            except:
                pass
        self.connected = False
        self.username = None
        self.session_id = None
        self.user_key = None
        logger.info("Desconectado del servidor")
    
    def _generate_unique_nonce(self) -> str:
        """Genera un nonce único no usado anteriormente."""
        nonce = generate_nonce()
        while nonce in self._used_nonces:
            nonce = generate_nonce()
        self._used_nonces.add(nonce)
        return nonce

    def _not_connected_response(self) -> Dict[str, Any]:
        """Respuesta estandar cuando no hay conexion activa."""
        response: Dict[str, Any] = {
            "success": False,
            "message": "No conectado al servidor",
        }
        if self.last_connect_error_code:
            response["code"] = self.last_connect_error_code
        return response

    def _transport_error_response(self, error: Exception) -> Dict[str, Any]:
        """Normaliza errores de transporte para respuestas al usuario."""
        if self.transport_mode == "PLAIN" and isinstance(
            error,
            (ProtocolError, ssl.SSLError, OSError, ConnectionResetError, BrokenPipeError),
        ):
            return {
                "success": False,
                "code": "TLS_REQUIRED",
                "message": "El servidor requiere TLS para esta conexion",
            }

        return {"success": False, "message": str(error)}
    
    def _create_message(
        self,
        msg_type: str,
        username: str,
        payload: Dict[str, Any],
        use_mac: bool = True
    ) -> Dict[str, Any]:
        """Crea un mensaje con timestamp, nonce y MAC."""
        msg_dict = {
            "type": msg_type,
            "ts": int(time.time() * 1000),
            "nonce": self._generate_unique_nonce(),
            "username": username,
            "payload": payload
        }
        
        if use_mac and self.user_key:
            canonical_bytes = canonicalize_message(msg_dict)
            mac = compute_hmac(self.user_key, canonical_bytes)
            msg_dict["mac"] = mac
        
        return msg_dict
    
    def register(self, username: str, password: str) -> Dict[str, Any]:
        """Registra un nuevo usuario."""
        if not self.connected:
            return self._not_connected_response()
        
        # REGISTER no lleva MAC (el usuario aún no existe)
        msg = self._create_message(
            "REGISTER",
            username,
            {"password": password},
            use_mac=False
        )
        
        try:
            send_message(self.sock, msg)
            response = receive_message(self.sock, timeout=MESSAGE_TIMEOUT)
            
            if response.get("success"):
                logger.info(f"Usuario '{username}' registrado exitosamente")
                self.user_key, self.user_key_salt = derive_user_key(
                    MASTER_KEY_BYTES,
                    username
                )
            
            return response
        
        except Exception as e:
            logger.error(f"Error en REGISTER: {e}")
            return self._transport_error_response(e)
    
    def login(self, username: str, password: str) -> Dict[str, Any]:
        """Inicia sesión."""
        if not self.connected:
            return self._not_connected_response()
        
        self.user_key, self.user_key_salt = derive_user_key(
            MASTER_KEY_BYTES,
            username
        )
        
        msg = self._create_message(
            "LOGIN",
            username,
            {"password": password}
        )
        
        try:
            send_message(self.sock, msg)
            response = receive_message(self.sock, timeout=MESSAGE_TIMEOUT)
            
            if response.get("success"):
                data = response.get("data", {})
                self.session_id = data.get("session_id")
                self.username = username
                logger.info(f"Login exitoso: usuario '{username}'")
            else:
                self.user_key = None
                self.user_key_salt = None
            
            return response
        
        except Exception as e:
            logger.error(f"Error en LOGIN: {e}")
            self.user_key = None
            return self._transport_error_response(e)
    
    def send_transaction(
        self,
        from_account: str,
        to_account: str,
        amount: str
    ) -> Dict[str, Any]:
        """Envía una transacción."""
        if not self.username or not self.user_key:
            return {"success": False, "message": "No autenticado"}
        
        msg = self._create_message(
            "TX",
            self.username,
            {
                "from_account": from_account,
                "to_account": to_account,
                "amount": amount
            }
        )
        
        try:
            send_message(self.sock, msg)
            response = receive_message(self.sock, timeout=MESSAGE_TIMEOUT)
            
            if response.get("success"):
                logger.info(f"Transacción enviada: {from_account} -> {to_account}: {amount}")
            
            return response
        
        except Exception as e:
            logger.error(f"Error en TX: {e}")
            return self._transport_error_response(e)
    
    def logout(self) -> Dict[str, Any]:
        """Cierra sesión."""
        if not self.username or not self.session_id:
            return {"success": False, "message": "No hay sesión activa"}
        
        msg = self._create_message(
            "LOGOUT",
            self.username,
            {"session_id": self.session_id}
        )
        
        try:
            send_message(self.sock, msg)
            response = receive_message(self.sock, timeout=MESSAGE_TIMEOUT)
            
            logger.info(f"Logout exitoso")
            
            self.session_id = None
            self.username = None
            self.user_key = None
            
            return response
        
        except Exception as e:
            logger.error(f"Error en LOGOUT: {e}")
            return self._transport_error_response(e)
    
    # ==================== SIMULACIÓN DE ATAQUES ====================
    
    def send_replay_attack(
        self,
        from_account: str,
        to_account: str,
        amount: str
    ) -> tuple:
        """Simula un ataque de replay enviando el mismo mensaje dos veces."""
        if not self.username or not self.user_key:
            error = {"success": False, "message": "No autenticado"}
            return error, error
        
        # Crear mensaje (mismo nonce)
        msg = self._create_message(
            "TX",
            self.username,
            {
                "from_account": from_account,
                "to_account": to_account,
                "amount": amount
            }
        )
        
        # Remover el nonce del set local para permitir reenvío
        if msg["nonce"] in self._used_nonces:
            self._used_nonces.remove(msg["nonce"])
        
        try:
            # Primera vez - debería funcionar
            logger.warning("⚠️  SIMULACIÓN DE ATAQUE: Enviando mensaje original...")
            send_message(self.sock, msg)
            resp1 = receive_message(self.sock, timeout=MESSAGE_TIMEOUT)
            
            time.sleep(0.5)
            
            # Segunda vez - debería ser rechazado (replay)
            logger.warning("⚠️  SIMULACIÓN DE ATAQUE: Reenviando mismo mensaje (REPLAY)...")
            send_message(self.sock, msg)
            resp2 = receive_message(self.sock, timeout=MESSAGE_TIMEOUT)
            
            return resp1, resp2
        
        except Exception as e:
            logger.error(f"Error en replay attack: {e}")
            error = {"success": False, "message": str(e)}
            return error, error
    
    def send_mitm_attack(
        self,
        from_account: str,
        to_account: str,
        amount: str,
        tampered_amount: str
    ) -> Dict[str, Any]:
        """Simula un ataque MITM modificando el payload tras calcular el MAC."""
        if not self.username or not self.user_key:
            return {"success": False, "message": "No autenticado"}
        
        # Crear mensaje legítimo
        msg = self._create_message(
            "TX",
            self.username,
            {
                "from_account": from_account,
                "to_account": to_account,
                "amount": amount
            }
        )
        
        # Modificar payload DESPUÉS de calcular MAC (simula MITM)
        logger.warning(
            f"⚠️  SIMULACIÓN DE ATAQUE MITM: "
            f"modificando amount de {amount} a {tampered_amount}"
        )
        msg["payload"]["amount"] = tampered_amount
        
        try:
            send_message(self.sock, msg)
            response = receive_message(self.sock, timeout=MESSAGE_TIMEOUT)
            return response
        
        except Exception as e:
            logger.error(f"Error en MITM attack: {e}")
            return {"success": False, "message": str(e)}
