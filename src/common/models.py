"""Modelos de datos para la comunicacion cliente-servidor."""
from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from enum import Enum


class MessageType(Enum):
    """Tipos de mensajes del protocolo."""
    REGISTER = "REGISTER"
    LOGIN = "LOGIN"
    TX = "TX"
    LOGOUT = "LOGOUT"
    PING = "PING"
    RESPONSE = "RESPONSE"
    ERROR = "ERROR"


@dataclass
class Message:
    """Estructura base de un mensaje del protocolo."""
    type: str
    username: str
    ts: int
    payload: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convierte el mensaje a diccionario."""
        return {
            "type": self.type,
            "username": self.username,
            "ts": self.ts,
            "payload": self.payload,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Message':
        """Crea un mensaje desde un diccionario."""
        return cls(
            type=data["type"],
            username=data["username"],
            ts=data["ts"],
            payload=data.get("payload", {}),
        )


@dataclass
class RegisterPayload:
    """Payload para registro de usuario."""
    password: str


@dataclass
class LoginPayload:
    """Payload para login."""
    password: str


@dataclass
class TransactionPayload:
    """Payload para transaccion financiera."""
    from_account: str
    to_account: str
    amount: str  # String para evitar problemas de precision en JSON


@dataclass
class Response:
    """Respuesta del servidor."""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    code: Optional[str] = None
