"""Servidor TCP para verificación de integridad en transacciones financieras."""
import socket
import ssl
import threading
import logging
import json
import time
import signal
import sys
from pathlib import Path
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
)
from .storage import Storage
from .security import SecurityManager
from .handlers import MessageHandler
from ..common.protocol import (
    send_message,
    receive_message,
    canonicalize_message,
    create_error_response,
    create_success_response
)
from ..common.crypto import verify_hmac, truncate_for_log
from ..common.transport import normalize_transport_mode, create_server_ssl_context
from ..common.models import Message
from ..common.errors import (
    InvalidMACError,
    ReplayAttackError,
    InvalidTimestampError,
    ProtocolError,
    SecurityError
)


# Configurar logging
LOG_DIR.mkdir(parents=True, exist_ok=True)

handlers = []
if LOG_TO_CONSOLE:
    handlers.append(logging.StreamHandler())
if LOG_TO_FILE:
    handlers.append(
        logging.FileHandler(LOG_DIR / "server.log", encoding='utf-8')
    )

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=handlers
)

logger = logging.getLogger(__name__)


class IntegrityServer:
    """Servidor TCP con verificación de integridad."""
    
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
        logger.info(f"Señal {signum} recibida, cerrando servidor...")
        self.stop()
        sys.exit(0)
    
    def start(self):
        """Inicia el servidor."""
        try:
            if self.transport_mode == "TLS":
                self.ssl_context = create_server_ssl_context(
                    cert_file=TLS_CERT_FILE,
                    key_file=TLS_KEY_FILE,
                    ca_file=TLS_CA_FILE,
                    min_version=TLS_MIN_VERSION,
                )

            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(MAX_CONNECTIONS)
            
            self.running = True
            logger.info(f"Transporte activo: {self.transport_mode}")
            
            logger.info(f"✓ Servidor de integridad iniciado en {self.host}:{self.port}")
            logger.info(f"✓ Esperando conexiones (máx: {MAX_CONNECTIONS})...")
            

            cleanup_thread = threading.Thread(target=self._periodic_cleanup, daemon=True)
            cleanup_thread.start()
            
            # Bucle principal
            while self.running:
                try:
                    client_socket, client_address = self.server_socket.accept()
                    
                    with self.connections_lock:
                        if self.active_connections >= MAX_CONNECTIONS:
                            logger.warning(f"Conexión rechazada (máximo alcanzado): {client_address}")
                            client_socket.close()
                            continue
                        
                        self.active_connections += 1

                    if self.transport_mode == "TLS":
                        try:
                            client_socket = self.ssl_context.wrap_socket(
                                client_socket,
                                server_side=True,
                            )
                        except ssl.SSLError as e:
                            logger.warning(f"Handshake TLS fallido desde {client_address}: {e}")
                            with self.connections_lock:
                                self.active_connections -= 1
                            client_socket.close()
                            continue
                    
                    logger.info(f"Nueva conexión desde {client_address} (activas: {self.active_connections})")
                    
                    client_thread = threading.Thread(
                        target=self._handle_client,
                        args=(client_socket, client_address),
                        daemon=True
                    )
                    client_thread.start()
                    
                except Exception as e:
                    if self.running:
                        logger.error(f"Error aceptando conexión: {e}")
        
        except Exception as e:
            logger.error(f"Error iniciando servidor: {e}", exc_info=True)
            self.stop()
    
    def stop(self):
        """Detiene el servidor."""
        self.running = False
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass
        logger.info("Servidor detenido")
    
    def _periodic_cleanup(self):
        """Limpia datos antiguos periódicamente."""
        while self.running:
            time.sleep(60)
            try:
                self.security.cleanup_old_data()
            except Exception as e:
                logger.error(f"Error en limpieza periódica: {e}")
    
    def _handle_client(self, client_socket: socket.socket, client_address: tuple):
        """Maneja la comunicación con un cliente."""
        client_ip = client_address[0]
        session_username: Optional[str] = None
        
        try:
            while self.running:
                try:
                    msg_dict = receive_message(client_socket, timeout=30.0)
                except ProtocolError as e:
                    if "cerrada" in str(e).lower():
                        break
                    logger.warning(f"Error de protocolo desde {client_ip}: {e}")
                    error_resp = create_error_response("PROTOCOL_ERROR", str(e))
                    send_message(client_socket, error_resp)
                    continue
                
                # Procesar
                try:
                    response = self._process_message(msg_dict, client_ip, session_username)
                    
                    # Si es LOGIN exitoso, guardar username de sesión
                    if (msg_dict.get("type") == "LOGIN" and 
                        response.get("success") and 
                        "data" in response):
                        session_username = response["data"].get("username")
                    
                    # Si es LOGOUT, limpiar sesión
                    if msg_dict.get("type") == "LOGOUT":
                        session_username = None
                    
                    send_message(client_socket, response)
                    
                except Exception as e:
                    logger.error(f"Error procesando mensaje: {e}", exc_info=True)
                    error_resp = create_error_response("INTERNAL_ERROR", "Error interno del servidor")
                    send_message(client_socket, error_resp)
        
        except Exception as e:
            logger.error(f"Error en comunicación con {client_ip}: {e}")
        
        finally:
            client_socket.close()
            with self.connections_lock:
                self.active_connections -= 1
            logger.info(f"Conexión cerrada: {client_ip} (activas: {self.active_connections})")
    
    def _process_message(
        self,
        msg_dict: dict,
        client_ip: str,
        session_username: Optional[str]
    ) -> dict:
        """Procesa un mensaje recibido y devuelve la respuesta."""
        msg_type = msg_dict.get("type")
        username = msg_dict.get("username", "")
        nonce = msg_dict.get("nonce", "")
        ts = msg_dict.get("ts", 0)
        payload = msg_dict.get("payload", {})
        mac = msg_dict.get("mac", "")
        
        logger.debug(f"Procesando {msg_type} de usuario '{username}' (IP: {client_ip})")
        
        if msg_type == "REGISTER":
            return self._handle_register(username, payload, client_ip, nonce, ts)
        
        # Resto de operaciones requieren verificación de integridad
        try:
            self.security.validate_timestamp(ts)
            
            user = self.storage.get_user(username)
            if not user:
                logger.warning(f"Mensaje de usuario inexistente: '{username}' (IP: {client_ip})")
                return create_error_response("AUTH_ERROR", "Usuario no autenticado")
            
            canonical_bytes = canonicalize_message(msg_dict)
            user_key = user["user_key"]
            
            if not verify_hmac(user_key, canonical_bytes, mac):
                logger.error(
                    f"MAC INVÁLIDO detectado: usuario '{username}' (IP: {client_ip}) - "
                    f"Posible MITM. MAC recibido: {truncate_for_log(mac)}"
                )
                raise InvalidMACError("MAC inválido (posible ataque MITM)")
            
            self.security.check_and_store_nonce(username, nonce, ts)
            
            if msg_type == "LOGIN":
                return self.handler.handle_login(username, payload, client_ip)
            
            elif msg_type == "TX":
                if not session_username or session_username != username:
                    logger.warning(
                        f"TX rechazada: usuario '{username}' sin sesión activa (IP: {client_ip})"
                    )
                    return create_error_response(
                        "AUTH_ERROR",
                        "Debe iniciar sesión antes de enviar transacciones"
                    )
                raw_message = json.dumps(msg_dict, sort_keys=True)
                mac_trunc = truncate_for_log(mac)
                return self.handler.handle_transaction(
                    username, payload, raw_message, mac_trunc, ts
                )
            
            elif msg_type == "LOGOUT":
                if not session_username or session_username != username:
                    logger.warning(
                        f"LOGOUT rechazado: usuario '{username}' sin sesión activa (IP: {client_ip})"
                    )
                    return create_error_response(
                        "AUTH_ERROR",
                        "No hay sesión activa para cerrar"
                    )
                return self.handler.handle_logout(username, payload)
            
            elif msg_type == "PING":
                return self.handler.handle_ping(username)
            
            else:
                return create_error_response("UNKNOWN_TYPE", f"Tipo de mensaje desconocido: {msg_type}")
        
        except InvalidMACError as e:
            return create_error_response("INVALID_MAC", str(e))
        
        except ReplayAttackError as e:
            return create_error_response("REPLAY_ATTACK", str(e))
        
        except InvalidTimestampError as e:
            return create_error_response("INVALID_TIMESTAMP", str(e))
        
        except SecurityError as e:
            return create_error_response("SECURITY_ERROR", str(e))
    
    def _handle_register(
        self,
        username: str,
        payload: dict,
        client_ip: str,
        nonce: str,
        ts: int
    ) -> dict:
        """Maneja REGISTER sin verificación de MAC (usuario nuevo)."""
        try:
            self.security.validate_timestamp(ts)
            
            try:
                self.security.check_and_store_nonce("REGISTER:" + username, nonce, ts)
            except ReplayAttackError:
                return create_error_response("REPLAY_ATTACK", "Solicitud de registro duplicada")
            
            return self.handler.handle_register(username, payload, client_ip)
        
        except InvalidTimestampError as e:
            return create_error_response("INVALID_TIMESTAMP", str(e))


def main():
    """Punto de entrada del servidor."""
    logger.info("=" * 60)
    logger.info("PAI2 - BYODSEC Road Warrior VPN SSL/TLS (Servidor)")
    logger.info("=" * 60)
    
    server = IntegrityServer()
    
    try:
        server.start()
    except KeyboardInterrupt:
        logger.info("Interrupción de teclado recibida")
        server.stop()


if __name__ == "__main__":
    main()
