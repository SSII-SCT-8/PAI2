"""Protocolo de comunicacion sobre TCP con framing."""
import json
import struct
import socket
from typing import Dict, Any, Optional
from .errors import ProtocolError


def send_message(sock: socket.socket, data: Dict[str, Any]) -> None:
    """Envia un mensaje con framing [4 bytes length][JSON payload]."""
    try:
        payload = json.dumps(data, ensure_ascii=False).encode('utf-8')
        length = struct.pack('>I', len(payload))
        sock.sendall(length + payload)
    except Exception as e:
        raise ProtocolError(f"Error enviando mensaje: {e}")


def receive_message(sock: socket.socket, timeout: Optional[float] = None) -> Dict[str, Any]:
    """Recibe un mensaje con framing por TCP."""
    try:
        original_timeout = sock.gettimeout()
        if timeout is not None:
            sock.settimeout(timeout)

        length_bytes = _recv_exact(sock, 4)
        if not length_bytes:
            raise ProtocolError("Conexion cerrada por el peer")

        payload_length = struct.unpack('>I', length_bytes)[0]

        max_message_size = 1024 * 1024  # 1 MB - evitar DoS
        if payload_length > max_message_size:
            raise ProtocolError(f"Mensaje demasiado grande: {payload_length} bytes")

        payload = _recv_exact(sock, payload_length)
        if len(payload) != payload_length:
            raise ProtocolError("Payload incompleto")

        data = json.loads(payload.decode('utf-8'))
        sock.settimeout(original_timeout)

        return data

    except json.JSONDecodeError as e:
        raise ProtocolError(f"JSON invalido: {e}")
    except socket.timeout:
        raise ProtocolError("Timeout esperando respuesta")
    except Exception as e:
        raise ProtocolError(f"Error recibiendo mensaje: {e}")


def _recv_exact(sock: socket.socket, n: int) -> bytes:
    """Recibe exactamente n bytes del socket."""
    data = b''
    while len(data) < n:
        chunk = sock.recv(n - len(data))
        if not chunk:
            break
        data += chunk
    return data


def create_error_response(code: str, message: str) -> Dict[str, Any]:
    """Crea una respuesta de error."""
    return {
        "type": "ERROR",
        "code": code,
        "message": message,
        "success": False,
    }


def create_success_response(message: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Crea una respuesta exitosa."""
    response = {
        "type": "RESPONSE",
        "message": message,
        "success": True,
    }
    if data:
        response["data"] = data
    return response
