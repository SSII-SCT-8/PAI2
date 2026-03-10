# PAI2 - BYODSEC Road Warrior VPN SSL/TLS

## 📋 Descripción

Sistema cliente-servidor de verificación de integridad para transacciones financieras mediante comunicación por sockets TCP. Implementa protección criptográfica contra ataques Man-in-the-Middle (MITM), Replay, Brute Force y canal lateral de tiempo (timing attacks).

**Contexto**: Según la política de seguridad, "En todas las transacciones por medios electrónicos no seguros se debe conservar la integridad de las comunicaciones". Este proyecto implementa esa política mediante técnicas criptográficas estándar.

## 🔒 Protecciones Implementadas

### 1. **Integridad (Anti-MITM)**
- **HMAC-SHA256** con claves de 256 bits
- Canonicalización determinista de mensajes (JSON ordenado)
- Verificación de MAC en cada mensaje

### 2. **Anti-Replay**
- Nonce único por mensaje (128 bits, criptográficamente seguro)
- Almacenamiento persistente de nonces usados (SQLite)
- Validación de timestamp con ventana configurable (5 minutos)

### 3. **Anti-Timing Attacks**
- Uso de `hmac.compare_digest()` para comparaciones en tiempo constante
- Evita fugas de información por diferencias de tiempo de ejecución

### 4. **Anti-Brute Force**
- Rate limiting configurable (5 intentos por defecto)
- Backoff exponencial (2^n segundos)
- Registro de intentos fallidos con ventana de tiempo (5 minutos)

### 5. **Protección de Credenciales**
- PBKDF2-HMAC-SHA256 con 150,000 iteraciones (OWASP 2023)
- Salt aleatorio por usuario (128 bits)
- Nunca se almacenan contraseñas en claro
- Derivación de claves por usuario con HKDF

## 🏗️ Arquitectura

```
PAI2/
├── src/
│   ├── common/           # Código compartido
│   │   ├── crypto.py     # HMAC, KDF, comparaciones seguras
│   │   ├── protocol.py   # Framing TCP, canonicalización
│   │   ├── models.py     # Dataclasses de mensajes
│   │   └── errors.py     # Excepciones personalizadas
│   │
│   ├── server/           # Servidor
│   │   ├── server.py     # Main TCP server con threading
│   │   ├── handlers.py   # Lógica REGISTER/LOGIN/TX/LOGOUT
│   │   ├── storage.py    # Persistencia SQLite
│   │   ├── security.py   # Nonce store, rate limiting, sesiones
│   │   └── config.py     # Configuración
│   │
│   └── client/           # Cliente
│       ├── client.py     # CLI interactiva
│       ├── api.py        # Comunicación con servidor
│       └── config.py     # Configuración
│
├── tests/                # Suite de tests
│   ├── test_crypto.py       # Tests de HMAC, KDF, etc.
│   ├── test_protocol.py     # Tests de framing y canonicalización
│   ├── test_replay.py       # Tests anti-replay
│   ├── test_mitm.py         # Tests anti-MITM
│   ├── test_rate_limit.py   # Tests anti-brute force
│   └── test_integration.py  # Tests end-to-end
│
├── config/               # Configuración
│   ├── seed_users.json      # Usuarios de demo
│   ├── seed_database.py     # Script de inicialización
│   ├── server.env.example   # Ejemplo de configuración servidor
│   └── client.env.example   # Ejemplo de configuración cliente
│
├── scripts/              # Scripts de utilidad
│   ├── demo_run.ps1         # Ejecutar demo completo
│   ├── run_tests.ps1        # Ejecutar todos los tests
│   └── clean.ps1            # Limpiar logs y BD
│
├── logs/                 # Logs del servidor y cliente
├── data/                 # Base de datos SQLite
└── README.md
```

## 📡 Protocolo de Comunicación

### Formato de Mensaje

Cada mensaje se envía con **framing TCP**:
```
[4 bytes: longitud (big-endian)] [N bytes: payload JSON UTF-8]
```

### Estructura JSON

```json
{
  "type": "REGISTER|LOGIN|TX|LOGOUT|PING",
  "ts": 1234567890000,
  "nonce": "base64_encoded_nonce_128_bits",
  "username": "alice",
  "payload": {
    "from_account": "ES1234",
    "to_account": "ES5678",
    "amount": "1000.00"
  },
  "mac": "base64_encoded_hmac_sha256"
}
```

### Flujo de Comunicación

1. **REGISTER**: Cliente → Servidor (crea usuario, NO requiere MAC)
2. **LOGIN**: Cliente → Servidor (autentica, retorna session_id)
3. **TX** (múltiples): Cliente → Servidor (envía transacciones)
4. **LOGOUT**: Cliente → Servidor (cierra sesión)

### Rechazo de Mensajes

El servidor rechaza mensajes si:
- ❌ **MAC inválido** → Posible MITM
- ❌ **Nonce repetido** → Replay attack
- ❌ **Timestamp fuera de ventana** → Mensaje antiguo/futuro

## 🔐 Seguridad: Tamaños de Clave

### ¿Por qué 256 bits y NO 32 bits?

**Clave de 32 bits:**
- Solo **2³² = 4,294,967,296** combinaciones posibles
- Una GPU moderna puede probar **>10⁹ hashes/segundo**
- **Tiempo para romper: ~4 segundos** ⚠️
- **INSEGURO** para uso en producción

**Clave de 256 bits:**
- **2²⁵⁶ ≈ 1.16 × 10⁷⁷** combinaciones posibles
- Incluso con 10⁹ intentos/segundo
- **Tiempo para romper: >10⁶⁰ años** ✅
- **Computacionalmente inviable** romper por fuerza bruta

**Implementado en el proyecto:**
- HMAC: Claves de **256 bits** (32 bytes)
- Nonces: **128 bits** (16 bytes) - suficiente para evitar colisiones
- Password salt: **128 bits** (16 bytes)

Ver: [`src/common/crypto.py`](src/common/crypto.py) para detalles de implementación.

## 🚀 Instalación y Ejecución

### Requisitos

- Python 3.11 o superior
- No requiere dependencias externas (solo biblioteca estándar)

### Instalación

```powershell
# 1. Clonar repositorio
git clone <repo-url>
cd PAI2

# 2. (Opcional) Crear entorno virtual
python -m venv venv
.\venv\Scripts\Activate.ps1

# 3. Inicializar base de datos con usuarios de prueba
python config\seed_database.py
```

### Ejecución con Script de Demo (Recomendado)

```powershell
.\scripts\demo_run.ps1
```

Modos dinámicos del demo:

```powershell
# Demo en modo PLAIN (por defecto)
.\scripts\demo_run.ps1 -Mode PLAIN

# Demo en modo TLS (genera certificados si faltan)
.\scripts\demo_run.ps1 -Mode TLS

# Forzar regeneración de certificados TLS
.\scripts\demo_run.ps1 -Mode TLS -GenerateCerts

# Mantener la base de datos actual (sin reiniciar)
.\scripts\demo_run.ps1 -Mode TLS -SkipDbReset
```

El script de demo:
1. Configura automáticamente `TRANSPORT_MODE` para servidor y cliente.
2. En modo `TLS`, prepara `TLS_CERT_FILE`, `TLS_KEY_FILE`, `TLS_CA_FILE`, `TLS_SERVER_HOSTNAME` y `TLS_MIN_VERSION`.
3. Inicia servidor y cliente en ventanas separadas.

### Ejecución con Scripts Individuales

Si prefieres más control, ejecuta servidor y cliente por separado:

```powershell
# Terminal 1: Ejecutar servidor
.\scripts\start_server.ps1

# Terminal 2 (nueva terminal): Ejecutar cliente
.\scripts\start_client.ps1
```

### Ejecución Manual Avanzada

**⚠️ IMPORTANTE**: El servidor corre indefinidamente (comportamiento normal). Necesitas DOS terminales separadas.

**Terminal 1 - Servidor:**
```powershell
python -m src.server.server
# El servidor se quedará ejecutando aquí (esto es correcto)
# Para detener: Ctrl+C
```

**Terminal 2 - Cliente (nueva terminal):**
```powershell
cd "C:\Users\Juan\Desktop\Carrera\4º\2º Cuatri\SSII\Mios\Github\PAI2"
python -m src.client.client
```

**Alternativa - Servidor en ventana separada:**
```powershell
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PWD'; python -m src.server.server"
Start-Sleep -Seconds 2
python -m src.client.client
```

## 👥 Usuarios de Prueba

Definidos en [`config/seed_users.json`](config/seed_users.json):

| Usuario | Password            |
|---------|---------------------|
| alice   | AliceSecure2024!    |
| bob     | BobPassword123#     |
| admin   | AdminPass2024$      |

**⚠️ IMPORTANTE**: Estos usuarios son solo para demostración. En producción, eliminar o cambiar las contraseñas.

## 🧪 Tests

### Ejecutar Todos los Tests

```powershell
.\scripts\run_tests.ps1
```

O manualmente:
```powershell
python -m unittest discover -s tests -p "test_*.py" -v
```

### Tests Incluidos

| Test | Descripción |
|------|-------------|
| `test_crypto.py` | HMAC, KDF, comparaciones seguras, análisis de fuerza de claves |
| `test_protocol.py` | Framing TCP, canonicalización JSON |
| `test_replay.py` | Detección de nonces repetidos |
| `test_mitm.py` | Detección de payloads modificados |
| `test_rate_limit.py` | Bloqueo tras múltiples intentos fallidos |
| `test_integration.py` | Ciclo completo: registro → login → TX → logout |

## 🎯 Modos de Simulación de Ataques

El cliente incluye modos interactivos para simular ataques:

### 1. Ataque Replay (Opción 5)

Envía el mismo mensaje dos veces para verificar que el servidor rechaza el segundo intento.

### 2. Ataque MITM (Opción 6)

Modifica el payload después de calcular el MAC para verificar que el servidor detecta la manipulación.

## 📊 Logs y Evidencias

Los logs se generan en el directorio `logs/`:

- **`server.log`**: Eventos del servidor (registro, login, transacciones, ataques detectados)
- **`client.log`**: Eventos del cliente

### Eventos Registrados

**Servidor:**
- ✅ Usuario registrado
- ✅ Login exitoso / ❌ Login fallido
- ✅ Transacción aceptada
- ❌ MAC inválido detectado (MITM)
- ❌ Nonce repetido detectado (Replay)
- ❌ Rate limit activado (Brute force)

**Seguridad de Logs:**
- **NO** se vuelcan secretos completos (claves, MACs, passwords)
- Secretos se truncan: `abc123...` (solo primeros 8 caracteres)

## 🛠️ Configuración

### Variables de Entorno (Opcional)

Copiar archivos de ejemplo:
```powershell
cp config\server.env.example .env
```

Variables disponibles:
```bash
# Servidor
SERVER_HOST=127.0.0.1
SERVER_PORT=9999
MASTER_KEY=CHANGE_THIS_IN_PRODUCTION_USE_256_BIT_KEY_MINIMUM
LOG_LEVEL=INFO
```

**⚠️ CRÍTICO**: En producción, generar una `MASTER_KEY` segura:
```powershell
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

## 🔍 Mitigaciones de Ataques

### Man-in-the-Middle (MITM)

**Ataque**: Atacante intercepta y modifica mensajes en tránsito.

**Mitigación**:
1. Cada mensaje incluye HMAC-SHA256 sobre todos los campos
2. El servidor recalcula el HMAC y verifica con `hmac.compare_digest()`
3. Si no coincide → mensaje rechazado con código `INVALID_MAC`

### Replay Attack

**Ataque**: Atacante captura un mensaje legítimo y lo reenvía.

**Mitigación**:
1. Cada mensaje incluye un nonce único (128 bits aleatorios)
2. El servidor almacena nonces usados en BD (tabla `nonces`)
3. Si el nonce ya existe → mensaje rechazado con código `REPLAY_ATTACK`

### Timing Attack (Canal Lateral de Tiempo)

**Ataque**: Medir el tiempo de respuesta para inferir información.

**Mitigación**:
1. Comparación de MACs con `hmac.compare_digest()` (tiempo constante)
2. Comparación de passwords con `hmac.compare_digest()` (tiempo constante)

### Brute Force (Adivinación de Passwords)

**Ataque**: Probar múltiples passwords hasta encontrar el correcto.

**Mitigación**:
1. Rate limiting: máximo N intentos fallidos por usuario (default: 5)
2. Backoff exponencial: bloqueo de 2^n segundos tras exceder el límite
3. Registro de intentos en BD para auditoría

## 🎓 Resumen Técnico

**Implementación de:**
- ✅ Comunicación por sockets TCP (no HTTP)
- ✅ HMAC-SHA256 para integridad (claves 256 bits)
- ✅ Nonce único + timestamp para anti-replay
- ✅ `hmac.compare_digest()` para anti-timing
- ✅ Rate limiting + backoff exponencial
- ✅ PBKDF2 (150k iter) para passwords
- ✅ HKDF para derivación de claves por usuario
- ✅ Persistencia SQLite (usuarios, transacciones, nonces, sesiones)
- ✅ Logs completos con eventos de seguridad
- ✅ Tests automatizados (100% cobertura de ataques)
- ✅ Modos de simulación de ataques (Replay, MITM)

**Ataques mitigados:**
- ✅ Man-in-the-Middle (HMAC)
- ✅ Replay (nonce store)
- ✅ Timing (comparaciones en tiempo constante)
- ✅ Brute Force (rate limiting)
- ✅ Key Derivation (claves >= 256 bits)

---

**Asignatura**: SSII - Seguridad en Sistemas Informáticos  
**Fecha**: Febrero 2026