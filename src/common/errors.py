"""
Excepciones personalizadas del sistema.
"""


class SecurityError(Exception):
    """Error base de seguridad."""
    pass


class RateLimitError(SecurityError):
    """Excedido el limite de intentos permitidos."""
    pass


class AuthenticationError(Exception):
    """Error de autenticacion."""
    pass


class UserAlreadyExistsError(Exception):
    """Usuario ya existe en el sistema."""
    pass


class SessionError(Exception):
    """Error relacionado con sesiones."""
    pass


class ProtocolError(Exception):
    """Error en el protocolo de comunicacion."""
    pass
