"""
Cliente interactivo CLI para el sistema de verificación de integridad.
"""
import logging
import sys
from pathlib import Path
from getpass import getpass

from .config import LOG_DIR, LOG_LEVEL, LOG_TO_FILE, LOG_TO_CONSOLE
from .api import ClientAPI


# Configurar logging
LOG_DIR.mkdir(parents=True, exist_ok=True)

handlers = []
if LOG_TO_CONSOLE:
    handlers.append(logging.StreamHandler())
if LOG_TO_FILE:
    handlers.append(
        logging.FileHandler(LOG_DIR / "client.log", encoding='utf-8')
    )

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=handlers
)

logger = logging.getLogger(__name__)


class InteractiveClient:
    """Cliente interactivo con menú."""
    
    def __init__(self):
        self.api = ClientAPI()
        self.running = True
    
    def show_banner(self):
        """Muestra el banner de bienvenida."""
        print("\n" + "=" * 70)
        print(" PAI2 - BYODSEC Road Warrior VPN SSL/TLS para Universidad Publica")
        print("=" * 70)
        print(" Protección implementada:")
        print("   ✓ HMAC-SHA256 para integridad (clave 256 bits)")
        print("   ✓ Nonce único por mensaje (anti-replay)")
        print("   ✓ Comparación en tiempo constante (anti-timing)")
        print("   ✓ Rate limiting y backoff exponencial (anti-brute force)")
        print("=" * 70 + "\n")
    
    def show_menu(self):
        """Muestra el menú principal."""
        if not self.api.username:
            print("\n--- MENÚ PRINCIPAL ---")
            print("1. Registrar nuevo usuario")
            print("2. Iniciar sesión")
            print("9. Salir")
        else:
            print(f"\n--- SESIÓN ACTIVA: {self.api.username} ---")
            print("3. Enviar transacción")
            print("4. Cerrar sesión")
            print("---")
            print("5. [SIMULACIÓN] Ataque Replay")
            print("6. [SIMULACIÓN] Ataque MITM")
            print("9. Salir")
        
        print()
    
    def run(self):
        """Ejecuta el bucle principal del cliente."""
        self.show_banner()
        
        # Conectar al servidor
        print("Conectando al servidor...")
        if not self.api.connect():
            print("❌ Error: No se pudo conectar al servidor")
            return
        
        print("✓ Conectado exitosamente\n")
        
        try:
            while self.running:
                self.show_menu()
                
                try:
                    choice = input("Seleccione una opción: ").strip()
                    
                    if choice == "1":
                        self._handle_register()
                    elif choice == "2":
                        self._handle_login()
                    elif choice == "3" and self.api.username:
                        self._handle_transaction()
                    elif choice == "4" and self.api.username:
                        self._handle_logout()
                    elif choice == "5" and self.api.username:
                        self._handle_replay_attack()
                    elif choice == "6" and self.api.username:
                        self._handle_mitm_attack()
                    elif choice == "9":
                        self.running = False
                    else:
                        print("❌ Opción inválida")
                
                except KeyboardInterrupt:
                    print("\n\n⚠️  Interrupción detectada")
                    self.running = False
                except EOFError:
                    print("\n\n⚠️  EOF detectado")
                    self.running = False
        
        finally:
            if self.api.username:
                print("\nCerrando sesión...")
                self.api.logout()
            
            print("Desconectando...")
            self.api.disconnect()
            print("Hasta luego!\n")
    
    def _handle_register(self):
        """Maneja el registro de usuario."""
        print("\n--- REGISTRO DE USUARIO ---")
        username = input("Usuario: ").strip()
        if not username:
            print("❌ Username no puede estar vacío")
            return
        
        password = getpass(prompt="Contraseña: ")
        if not password:
            print("❌ Password no puede estar vacío")
            return
        
        print("\nRegistrando usuario...")
        response = self.api.register(username, password)
        
        if response.get("success"):
            print(f"✓ {response.get('message')}")
            print("  Ahora puede iniciar sesión (opción 2)")
        else:
            print(f"❌ Error: {response.get('message')}")
    
    def _handle_login(self):
        """Maneja el inicio de sesión."""
        print("\n--- INICIO DE SESIÓN ---")
        username = input("Usuario: ").strip()
        if not username:
            print("❌ Username no puede estar vacío")
            return
        
        password = getpass("Contraseña: ")
        if not password:
            print("❌ Password no puede estar vacío")
            return
        
        print("\nIniciando sesión...")
        response = self.api.login(username, password)
        
        if response.get("success"):
            print(f"✓ {response.get('message')}")
            print(f"  Sesión iniciada como: {username}")
        else:
            print(f"❌ Error: {response.get('message')}")
    
    def _handle_transaction(self):
        """Maneja el envío de transacciones."""
        print("\n--- ENVIAR TRANSACCIÓN ---")
        print("Formato: Cuenta origen, Cuenta destino, Cantidad")
        
        from_account = input("Cuenta origen: ").strip()
        to_account = input("Cuenta destino: ").strip()
        amount = input("Cantidad: ").strip()
        
        if not all([from_account, to_account, amount]):
            print("❌ Todos los campos son obligatorios")
            return
        
        print("\nEnviando transacción con protección de integridad...")
        response = self.api.send_transaction(from_account, to_account, amount)
        
        if response.get("success"):
            print(f"✓ {response.get('message')}")
            data = response.get('data', {})
            if data:
                print(f"  ID de transacción: {data.get('transaction_id')}")
                print(f"  {data.get('from_account')} → {data.get('to_account')}: {data.get('amount')}")
        else:
            print(f"❌ Error: {response.get('message')}")
            code = response.get('code', '')
            if code == 'INVALID_MAC':
                print("  ⚠️  Se detectó modificación del mensaje (MITM)")
            elif code == 'REPLAY_ATTACK':
                print("  ⚠️  Se detectó reutilización de mensaje (Replay)")
    
    def _handle_logout(self):
        """Maneja el cierre de sesión."""
        print("\nCerrando sesión...")
        response = self.api.logout()
        
        if response.get("success"):
            print(f"✓ {response.get('message')}")
        else:
            print(f"⚠️  {response.get('message')}")
    
    def _handle_replay_attack(self):
        """Simula un ataque de replay."""
        print("\n--- SIMULACIÓN DE ATAQUE REPLAY ---")
        print("⚠️  Este modo enviará el MISMO mensaje DOS veces")
        print("    El servidor debería RECHAZAR el segundo intento\n")
        
        confirm = input("¿Continuar? (s/n): ").strip().lower()
        if confirm != 's':
            print("Cancelado")
            return
        
        from_account = input("Cuenta origen: ").strip()
        to_account = input("Cuenta destino: ").strip()
        amount = input("Cantidad: ").strip()
        
        if not all([from_account, to_account, amount]):
            print("❌ Todos los campos son obligatorios")
            return
        
        print("\n🔴 Ejecutando ataque de replay...")
        resp1, resp2 = self.api.send_replay_attack(from_account, to_account, amount)
        
        print("\n--- RESULTADO PRIMER ENVÍO ---")
        if resp1.get("success"):
            print(f"✓ {resp1.get('message')}")
        else:
            print(f"❌ {resp1.get('message')}")
        
        print("\n--- RESULTADO SEGUNDO ENVÍO (REPLAY) ---")
        if resp2.get("success"):
            print(f"⚠️  VULNERABLE: El servidor aceptó el mensaje repetido!")
            print(f"   {resp2.get('message')}")
        else:
            print(f"✓ PROTEGIDO: El servidor rechazó el replay")
            print(f"   Mensaje: {resp2.get('message')}")
            print(f"   Código: {resp2.get('code')}")
    
    def _handle_mitm_attack(self):
        """Simula un ataque MITM."""
        print("\n--- SIMULACIÓN DE ATAQUE MITM ---")
        print("⚠️  Este modo modificará el payload DESPUÉS de calcular el MAC")
        print("    El servidor debería RECHAZAR por MAC inválido\n")
        
        confirm = input("¿Continuar? (s/n): ").strip().lower()
        if confirm != 's':
            print("Cancelado")
            return
        
        from_account = input("Cuenta origen: ").strip()
        to_account = input("Cuenta destino: ").strip()
        amount = input("Cantidad original: ").strip()
        tampered_amount = input("Cantidad modificada (MITM): ").strip()
        
        if not all([from_account, to_account, amount, tampered_amount]):
            print("❌ Todos los campos son obligatorios")
            return
        
        print("\n🔴 Ejecutando ataque MITM...")
        response = self.api.send_mitm_attack(from_account, to_account, amount, tampered_amount)
        
        print("\n--- RESULTADO ---")
        if response.get("success"):
            print(f"⚠️  VULNERABLE: El servidor aceptó el mensaje modificado!")
            print(f"   {response.get('message')}")
        else:
            print(f"✓ PROTEGIDO: El servidor rechazó el mensaje modificado")
            print(f"   Mensaje: {response.get('message')}")
            print(f"   Código: {response.get('code')}")


def main():
    """Punto de entrada del cliente."""
    client = InteractiveClient()
    
    try:
        client.run()
    except Exception as e:
        logger.error(f"Error fatal: {e}", exc_info=True)
        print(f"\n❌ Error fatal: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
