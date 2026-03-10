# Estructura del Proyecto PAI2

## Visión General

Este proyecto implementa un sistema cliente-servidor de verificación de integridad para transacciones financieras con protección criptográfica contra ataques MITM, replay, brute force y timing.

## Árbol de Directorios

```
PAI2/
│
├── src/                          # Código fuente principal
│   ├── common/                   # Módulos compartidos entre cliente y servidor
│   │   ├── __init__.py
│   │   ├── crypto.py             # HMAC, KDF, hashing de passwords
│   │   ├── protocol.py           # Framing TCP, canonicalización JSON
│   │   ├── models.py             # Dataclasses de mensajes
│   │   └── errors.py             # Excepciones personalizadas
│   │
│   ├── server/                   # Servidor TCP
│   │   ├── __init__.py
│   │   ├── server.py             # Main TCP server (threading)
│   │   ├── handlers.py           # Lógica REGISTER/LOGIN/TX/LOGOUT
│   │   ├── storage.py            # Persistencia SQLite
│   │   ├── security.py           # Rate limit, nonces, sesiones
│   │   └── config.py             # Configuración del servidor
│   │
│   └── client/                   # Cliente TCP
│       ├── __init__.py
│       ├── client.py             # Interfaz de línea de comandos
│       ├── api.py                # API de cliente (lógica de comunicación)
│       └── config.py             # Configuración del cliente
│
├── tests/                        # Tests unitarios e integración
│   ├── test_crypto.py            # Tests de funciones criptográficas
│   ├── test_protocol.py          # Tests de protocolo y framing
│   ├── test_mitm.py              # Tests de protección contra MITM
│   ├── test_replay.py            # Tests de protección anti-replay
│   ├── test_rate_limit.py        # Tests de rate limiting
│   ├── test_security.py          # Tests de seguridad completos
│   ├── test_integration.py       # Tests de ciclo completo
│   └── test_cliente.py           # Tests de cliente (mocks)
│
├── scripts/                      # Scripts de utilidad (PowerShell)
│   ├── start_server.ps1          # Iniciar servidor
│   ├── start_client.ps1          # Iniciar cliente
│   ├── demo_run.ps1              # Demo completo (servidor + cliente)
│   ├── run_tests.ps1             # Ejecutar tests
│   ├── clean.ps1                 # Limpiar logs y BD
│   └── cleanup_project.ps1       # Limpiar carpetas obsoletas
│
├── config/                       # Configuración y datos iniciales
│   ├── server.env.example        # Ejemplo de configuración del servidor
│   ├── client.env.example        # Ejemplo de configuración del cliente
│   ├── seed_database.py          # Script para crear usuarios de prueba
│   └── seed_users.json           # Usuarios de prueba
│
├── data/                         # Base de datos SQLite (runtime)
│   └── server.db                 # BD del servidor (generado en tiempo de ejecución)
│
├── logs/                         # Logs del sistema (runtime)
│   ├── server.log                # Log del servidor
│   └── client.log                # Log del cliente
│
├── docs/                         # Documentación adicional
│
├── .env                          # Variables de entorno (NO VERSIONADO)
├── .env.example                  # Ejemplo de variables de entorno
├── .gitignore                    # Archivos ignorados por Git
├── requirements.txt              # Dependencias de Python
├── readme.md                     # Documentación principal
└── STRUCTURE.md                  # Este archivo
```

## Componentes Principales

### 1. **src/common/** - Código Compartido

- **crypto.py**: Funciones criptográficas (HMAC-SHA256, PBKDF2, HKDF, comparaciones seguras)
- **protocol.py**: Protocolo de comunicación TCP con framing y canonicalización JSON
- **models.py**: Definición de estructuras de datos (Message, User, Transaction)
- **errors.py**: Excepciones personalizadas (InvalidMACError, ReplayAttackError, etc.)

### 2. **src/server/** - Servidor

- **server.py**: Servidor TCP multi-threaded, gestión de conexiones, validación de mensajes
- **handlers.py**: Lógica de negocio para cada tipo de mensaje (REGISTER, LOGIN, TX, LOGOUT)
- **storage.py**: Capa de persistencia SQLite (usuarios, sesiones, transacciones, nonces)
- **security.py**: Gestión de seguridad (rate limiting, validación de timestamps, anti-replay)
- **config.py**: Parámetros de configuración del servidor

### 3. **src/client/** - Cliente

- **client.py**: Interfaz de línea de comandos interactiva
- **api.py**: API de cliente con métodos para register, login, send_transaction, logout
- **config.py**: Parámetros de configuración del cliente

### 4. **tests/** - Suite de Tests

51 tests automatizados que cubren:
- Funciones criptográficas (HMAC, KDF, hashing)
- Protocolo de comunicación (framing, canonicalización)
- Protección contra ataques (MITM, replay, brute force, timing)
- Integración completa (ciclo de vida de usuario)

## Flujo de Ejecución

### 1. Inicialización del Servidor

```bash
python -m src.server.server
# o usar: .\scripts\start_server.ps1
```

- Carga configuración (host, puerto, master key)
- Inicializa base de datos SQLite
- Inicia servidor TCP en puerto 9999
- Escucha conexiones (máximo 10 concurrentes)

### 2. Inicialización del Cliente

```bash
python -m src.client.client
# o usar: .\scripts\start_client.ps1
```

- Conecta al servidor en localhost:9999
- Presenta menú interactivo
- Permite registro, login, transacciones, logout

### 3. Ciclo de Transacción

1. **REGISTER**: Usuario se registra con username y password
2. **LOGIN**: Se autentica y recibe session_id
3. **TX**: Envía transacciones (requiere sesión activa)
4. **LOGOUT**: Cierra sesión

Cada mensaje (excepto REGISTER) incluye:
- Username
- Nonce único (anti-replay)
- Timestamp (ventana de 5 minutos)
- Payload (datos específicos del mensaje)
- MAC (HMAC-SHA256 para integridad)

## Protecciones de Seguridad

### Anti-MITM
- HMAC-SHA256 con claves de 256 bits
- Verificación de MAC en cada mensaje
- Canonicalización determinista (JSON ordenado)

### Anti-Replay
- Nonce único por mensaje (128 bits)
- Almacenamiento persistente en SQLite
- Constraint UNIQUE(username, nonce)

### Anti-Timing
- `hmac.compare_digest()` para comparaciones
- Evita fugas por timing side-channel

### Anti-Brute Force
- Rate limiting: 5 intentos por usuario
- Backoff exponencial: 2^n segundos
- Ventana de 5 minutos

## Gestión de Dependencias

Todas las dependencias están en `requirements.txt` (actualmente solo librerías estándar de Python 3.10+).

## Archivos Ignorados (.gitignore)

- `__pycache__/` - Cachés de Python
- `.pytest_cache/` - Caché de pytest
- `.venv/` - Entorno virtual
- `.env` - Variables de entorno locales
- `*.db` - Bases de datos
- `logs/*.log` - Archivos de log

## Carpetas Eliminadas (Obsoletas)

Las siguientes carpetas formaban parte de una versión anterior del proyecto y han sido eliminadas:

- ~~`cliente/`~~ → Migrado a `src/client/`
- ~~`servidor/`~~ → Migrado a `src/server/`

Para limpiar estas carpetas si vuelven a aparecer, ejecutar:
```powershell
.\scripts\cleanup_project.ps1
```

## Ejecución de Tests

```bash
# Todos los tests
python -m unittest discover -s tests -p "test_*.py" -v

# Test específico
python -m unittest tests.test_crypto -v

# Con script
.\scripts\run_tests.ps1
```

## Logs

Los logs se generan automáticamente en `logs/`:
- **server.log**: Eventos del servidor (LOGIN, TX, errores, ataques detectados)
- **client.log**: Eventos del cliente (conexiones, envíos, respuestas)

Los logs **NO incluyen secretos** (passwords, MACs completos, claves).
