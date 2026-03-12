"""
Cliente interactivo CLI.
"""
import logging
import sys
from getpass import getpass

from .config import LOG_DIR, LOG_LEVEL, LOG_TO_FILE, LOG_TO_CONSOLE
from .api import ClientAPI


LOG_DIR.mkdir(parents=True, exist_ok=True)

handlers = []
if LOG_TO_CONSOLE:
    handlers.append(logging.StreamHandler())
if LOG_TO_FILE:
    handlers.append(logging.FileHandler(LOG_DIR / "client.log", encoding="utf-8"))

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=handlers,
)

logger = logging.getLogger(__name__)


class InteractiveClient:
    """Cliente interactivo con menu."""

    def __init__(self):
        self.api = ClientAPI()
        self.running = True

    def show_banner(self):
        """Muestra el banner de bienvenida."""
        print("\n" + "=" * 70)
        print(" PAI2 - BYODSEC Road Warrior VPN SSL/TLS para Universidad Publica")
        print("=" * 70)
        print(" Proteccion implementada:")
        print("   * TLS 1.3 obligatorio")
        print("   * Verificacion de certificado del servidor")
        print("   * Rate limiting y backoff exponencial (anti-brute force)")
        print("=" * 70 + "\n")

    def show_menu(self):
        """Muestra el menu principal."""
        if not self.api.username:
            print("\n--- MENU PRINCIPAL ---")
            print("1. Registrar nuevo usuario")
            print("2. Iniciar sesion")
            print("9. Salir")
        else:
            print(f"\n--- SESION ACTIVA: {self.api.username} ---")
            print("3. Enviar mensaje")
            print("4. Ver historial")
            print("5. Cerrar sesion")
            print("9. Salir")

        print()

    def run(self):
        """Ejecuta el bucle principal del cliente."""
        self.show_banner()

        print("Conectando al servidor...")
        if not self.api.connect():
            print("Error: No se pudo conectar al servidor")
            return

        print("Conectado exitosamente\n")

        try:
            while self.running:
                self.show_menu()

                try:
                    choice = input("Seleccione una opcion: ").strip()

                    if choice == "1":
                        self._handle_register()
                    elif choice == "2":
                        self._handle_login()
                    elif choice == "3" and self.api.username:
                        self._handle_send_message()
                    elif choice == "4" and self.api.username:
                        self._handle_history()
                    elif choice == "5" and self.api.username:
                        self._handle_logout()
                    elif choice == "9":
                        self.running = False
                    else:
                        print("Opcion invalida")

                except KeyboardInterrupt:
                    print("\n\nInterrupcion detectada")
                    self.running = False
                except EOFError:
                    print("\n\nEOF detectado")
                    self.running = False

        finally:
            if self.api.username:
                print("\nCerrando sesion...")
                self.api.logout()

            print("Desconectando...")
            self.api.disconnect()
            print("Hasta luego\n")

    def _handle_register(self):
        """Maneja el registro de usuario."""
        print("\n--- REGISTRO DE USUARIO ---")
        username = input("Usuario: ").strip()
        if not username:
            print("Username no puede estar vacio")
            return

        password = getpass(prompt="Contrasena: ")
        if not password:
            print("Password no puede estar vacio")
            return

        print("\nRegistrando usuario...")
        response = self.api.register(username, password)

        if response.get("success"):
            print(response.get("message"))
            print("Ahora puede iniciar sesion (opcion 2)")
        else:
            print(f"Error: {response.get('message')}")

    def _handle_login(self):
        """Maneja el inicio de sesion."""
        print("\n--- INICIO DE SESION ---")
        username = input("Usuario: ").strip()
        if not username:
            print("Username no puede estar vacio")
            return

        password = getpass("Contrasena: ")
        if not password:
            print("Password no puede estar vacio")
            return

        print("\nIniciando sesion...")
        response = self.api.login(username, password)

        if response.get("success"):
            print(response.get("message"))
            print(f"Sesion iniciada como: {username}")
        else:
            print(f"Error: {response.get('message')}")

    def _handle_send_message(self):
        """Maneja el envio de mensajes de texto."""
        print("\n--- ENVIAR MENSAJE ---")
        print("Longitud permitida: 1..144 caracteres")

        text = input("Mensaje: ").rstrip("\n")

        print("\nEnviando mensaje...")
        response = self.api.send_message_text(text)

        if response.get("success"):
            print(response.get("message"))
            data = response.get("data", {})
            if data:
                print(f"ID de mensaje: {data.get('message_id')}")
                print(f"Total mensajes: {data.get('total_messages')}")
        else:
            print(f"Error: {response.get('message')}")

    def _handle_history(self):
        """Maneja la consulta de historial de mensajes."""
        print("\n--- HISTORIAL DE MENSAJES ---")
        raw_limit = input("Limite (Enter para 50): ").strip()

        limit = None
        if raw_limit:
            try:
                limit = int(raw_limit)
            except ValueError:
                print("Error: el limite debe ser un numero entero")
                return

        response = self.api.get_history(limit=limit)
        if not response.get("success"):
            print(f"Error: {response.get('message')}")
            return

        data = response.get("data", {})
        messages = data.get("messages", [])

        print(response.get("message"))
        print(f"Total historico: {data.get('total_messages', 0)}")
        print(f"Mensajes devueltos: {len(messages)}")

        for item in messages:
            print(f"- [{item.get('ts')}] {item.get('message_text')}")

    def _handle_logout(self):
        """Maneja el cierre de sesion."""
        print("\nCerrando sesion...")
        response = self.api.logout()

        if response.get("success"):
            print(response.get("message"))
        else:
            print(response.get("message"))


def main():
    """Punto de entrada del cliente."""
    client = InteractiveClient()

    try:
        client.run()
    except Exception as e:
        logger.error(f"Error fatal: {e}", exc_info=True)
        print(f"\nError fatal: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
