# PAI2 - BYODSEC Road Warrior VPN SSL/TLS

## ðŸ“‹ DescripciÃ³n

Sistema cliente-servidor de verificaciÃ³n de integridad para transacciones financieras mediante comunicaciÃ³n por sockets TCP. Implementa protecciÃ³n criptogrÃ¡fica contra ataques Man-in-the-Middle (MITM), Replay, Brute Force y canal lateral de tiempo (timing attacks).

**Contexto**: SegÃºn la polÃ­tica de seguridad, "En todas las transacciones por medios electrÃ³nicos no seguros se debe conservar la integridad de las comunicaciones". Este proyecto implementa esa polÃ­tica mediante tÃ©cnicas criptogrÃ¡ficas estÃ¡ndar.

## Estado PAI2 (2026-03-10)

- Bloque 1 (Nucleo transporte/seguridad): completado.
- Bloque 2 (Operacion y DX): completado.
- Flujo funcional actual: `REGISTER`, `LOGIN`, `TX`, `LOGOUT`.
- Pendiente para cierre funcional PAI2: migracion `TX -> MSG`, limite 1..144, historial y contador por usuario (bloque B del plan).
## ðŸ”’ Protecciones Implementadas

### 1. **Integridad (Anti-MITM)**
- **HMAC-SHA256** con claves de 256 bits
- CanonicalizaciÃ³n determinista de mensajes (JSON ordenado)
- VerificaciÃ³n de MAC en cada mensaje

### 2. **Anti-Replay**
- Nonce Ãºnico por mensaje (128 bits, criptogrÃ¡ficamente seguro)
- Almacenamiento persistente de nonces usados (SQLite)
- ValidaciÃ³n de timestamp con ventana configurable (5 minutos)

### 3. **Anti-Timing Attacks**
- Uso de `hmac.compare_digest()` para comparaciones en tiempo constante
- Evita fugas de informaciÃ³n por diferencias de tiempo de ejecuciÃ³n

### 4. **Anti-Brute Force**
- Rate limiting configurable (5 intentos por defecto)
- Backoff exponencial (2^n segundos)
- Registro de intentos fallidos con ventana de tiempo (5 minutos)

### 5. **ProtecciÃ³n de Credenciales**
- PBKDF2-HMAC-SHA256 con 150,000 iteraciones (OWASP 2023)
- Salt aleatorio por usuario (128 bits)
- Nunca se almacenan contraseÃ±as en claro
- DerivaciÃ³n de claves por usuario con HKDF

## ðŸ—ï¸ Arquitectura

```
PAI2/
â”œâ”€â”€ src/
â”‚   â”œâ”€â”€ common/           # CÃ³digo compartido
â”‚   â”‚   â”œâ”€â”€ crypto.py     # HMAC, KDF, comparaciones seguras
â”‚   â”‚   â”œâ”€â”€ protocol.py   # Framing TCP, canonicalizaciÃ³n
â”‚   â”‚   â”œâ”€â”€ models.py     # Dataclasses de mensajes
â”‚   â”‚   â””â”€â”€ errors.py     # Excepciones personalizadas
â”‚   â”‚
â”‚   â”œâ”€â”€ server/           # Servidor
â”‚   â”‚   â”œâ”€â”€ server.py     # Main TCP server con threading
â”‚   â”‚   â”œâ”€â”€ handlers.py   # LÃ³gica REGISTER/LOGIN/TX/LOGOUT
â”‚   â”‚   â”œâ”€â”€ storage.py    # Persistencia SQLite
â”‚   â”‚   â”œâ”€â”€ security.py   # Nonce store, rate limiting, sesiones
â”‚   â”‚   â””â”€â”€ config.py     # ConfiguraciÃ³n
â”‚   â”‚
â”‚   â””â”€â”€ client/           # Cliente
â”‚       â”œâ”€â”€ client.py     # CLI interactiva
â”‚       â”œâ”€â”€ api.py        # ComunicaciÃ³n con servidor
â”‚       â””â”€â”€ config.py     # ConfiguraciÃ³n
â”‚
â”œâ”€â”€ tests/                # Suite de tests
â”‚   â”œâ”€â”€ test_crypto.py       # Tests de HMAC, KDF, etc.
â”‚   â”œâ”€â”€ test_protocol.py     # Tests de framing y canonicalizaciÃ³n
â”‚   â”œâ”€â”€ test_replay.py       # Tests anti-replay
â”‚   â”œâ”€â”€ test_mitm.py         # Tests anti-MITM
â”‚   â”œâ”€â”€ test_rate_limit.py   # Tests anti-brute force
â”‚   â””â”€â”€ test_integration.py  # Tests end-to-end
â”‚
â”œâ”€â”€ config/               # ConfiguraciÃ³n
â”‚   â”œâ”€â”€ seed_users.json      # Usuarios de demo
â”‚   â”œâ”€â”€ seed_database.py     # Script de inicializaciÃ³n
â”‚   â”œâ”€â”€ server.env.example   # Ejemplo de configuraciÃ³n servidor
â”‚   â””â”€â”€ client.env.example   # Ejemplo de configuraciÃ³n cliente
â”‚
â”œâ”€â”€ scripts/              # Scripts de utilidad
â”‚   â”œâ”€â”€ demo_run.ps1         # Ejecutar demo completo
â”‚   â”œâ”€â”€ run_tests.ps1        # Ejecutar todos los tests
â”‚   â””â”€â”€ clean.ps1            # Limpiar logs y BD
â”‚
â”œâ”€â”€ logs/                 # Logs del servidor y cliente
â”œâ”€â”€ data/                 # Base de datos SQLite
â””â”€â”€ readme.md
```

## ðŸ“¡ Protocolo de ComunicaciÃ³n

### Formato de Mensaje

Cada mensaje se envÃ­a con **framing TCP**:
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

### Flujo de ComunicaciÃ³n

1. **REGISTER**: Cliente â†’ Servidor (crea usuario, NO requiere MAC)
2. **LOGIN**: Cliente â†’ Servidor (autentica, retorna session_id)
3. **TX** (mÃºltiples): Cliente â†’ Servidor (envÃ­a transacciones)
4. **LOGOUT**: Cliente â†’ Servidor (cierra sesiÃ³n)

### Rechazo de Mensajes

El servidor rechaza mensajes si:
- âŒ **MAC invÃ¡lido** â†’ Posible MITM
- âŒ **Nonce repetido** â†’ Replay attack
- âŒ **Timestamp fuera de ventana** â†’ Mensaje antiguo/futuro

## ðŸ” Seguridad: TamaÃ±os de Clave

### Â¿Por quÃ© 256 bits y NO 32 bits?

**Clave de 32 bits:**
- Solo **2Â³Â² = 4,294,967,296** combinaciones posibles
- Una GPU moderna puede probar **>10â¹ hashes/segundo**
- **Tiempo para romper: ~4 segundos** âš ï¸
- **INSEGURO** para uso en producciÃ³n

**Clave de 256 bits:**
- **2Â²âµâ¶ â‰ˆ 1.16 Ã— 10â·â·** combinaciones posibles
- Incluso con 10â¹ intentos/segundo
- **Tiempo para romper: >10â¶â° aÃ±os** âœ…
- **Computacionalmente inviable** romper por fuerza bruta

**Implementado en el proyecto:**
- HMAC: Claves de **256 bits** (32 bytes)
- Nonces: **128 bits** (16 bytes) - suficiente para evitar colisiones
- Password salt: **128 bits** (16 bytes)

Ver: [`src/common/crypto.py`](src/common/crypto.py) para detalles de implementaciÃ³n.

## ðŸš€ InstalaciÃ³n y EjecuciÃ³n

### Requisitos

- Python 3.11 o superior
- Requiere instalar dependencias de `requirements.txt` (`cryptography` y `python-dotenv`)

### InstalaciÃ³n

```powershell
# 1. Clonar repositorio
git clone <repo-url>
cd PAI2

# 2. (Opcional) Crear entorno virtual
python -m venv venv
.\venv\Scripts\Activate.ps1

# 3. Instalar dependencias
python -m pip install -r requirements.txt

# 4. Inicializar base de datos con usuarios de prueba
python config\seed_database.py
```

### EjecuciÃ³n con Script de Demo (Recomendado)

```powershell
.\scripts\demo_run.ps1
```

Modos dinÃ¡micos del demo:

```powershell
# Demo en modo PLAIN (por defecto)
.\scripts\demo_run.ps1 -Mode PLAIN

# Demo en modo TLS (genera certificados si faltan)
.\scripts\demo_run.ps1 -Mode TLS

# Forzar regeneraciÃ³n de certificados TLS
.\scripts\demo_run.ps1 -Mode TLS -GenerateCerts

# Mantener la base de datos actual (sin reiniciar)
.\scripts\demo_run.ps1 -Mode TLS -SkipDbReset
```

El script de demo:
1. Configura automÃ¡ticamente `TRANSPORT_MODE` para servidor y cliente.
2. En modo `TLS`, prepara `TLS_CERT_FILE`, `TLS_KEY_FILE`, `TLS_CA_FILE`, `TLS_SERVER_HOSTNAME` y `TLS_MIN_VERSION`.
3. Inicia servidor y cliente en ventanas separadas.

### EjecuciÃ³n con Scripts Individuales

Si prefieres mÃ¡s control, ejecuta servidor y cliente por separado:

```powershell
# Terminal 1: Ejecutar servidor
.\scripts\start_server.ps1

# Terminal 2 (nueva terminal): Ejecutar cliente
.\scripts\start_client.ps1
```

### EjecuciÃ³n Manual Avanzada

**âš ï¸ IMPORTANTE**: El servidor corre indefinidamente (comportamiento normal). Necesitas DOS terminales separadas.

**Terminal 1 - Servidor:**
```powershell
python -m src.server.server
# El servidor se quedarÃ¡ ejecutando aquÃ­ (esto es correcto)
# Para detener: Ctrl+C
```

**Terminal 2 - Cliente (nueva terminal):**
```powershell
cd "C:\Users\Juan\Desktop\Carrera\4Âº\2Âº Cuatri\SSII\Mios\Github\PAI2"
python -m src.client.client
```

**Alternativa - Servidor en ventana separada:**
```powershell
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PWD'; python -m src.server.server"
Start-Sleep -Seconds 2
python -m src.client.client
```

## ðŸ‘¥ Usuarios de Prueba

Definidos en [`config/seed_users.json`](config/seed_users.json):

| Usuario | Password            |
|---------|---------------------|
| alice   | AliceSecure2024!    |
| bob     | BobPassword123#     |
| admin   | AdminPass2024$      |

**âš ï¸ IMPORTANTE**: Estos usuarios son solo para demostraciÃ³n. En producciÃ³n, eliminar o cambiar las contraseÃ±as.

## ðŸ§ª Tests

### Ejecutar Todos los Tests

```powershell
.\scripts\run_tests.ps1
```

O manualmente:
```powershell
python -m unittest discover -s tests -p "test_*.py" -v
```

### Tests Incluidos

| Test | Descripcion |
|------|-------------|
| `test_crypto.py` | HMAC, KDF, comparaciones seguras y fuerza de claves |
| `test_protocol.py` | Framing TCP y canonicalizacion JSON |
| `test_replay.py` | Deteccion de nonces repetidos |
| `test_mitm.py` | Deteccion de payloads modificados |
| `test_rate_limit.py` | Bloqueo tras multiples intentos fallidos |
| `test_transport_tls.py` | Validacion de configuracion TLS y endurecimiento |
| `test_tls_transport_integration.py` | Integracion TLS: valido, cert invalido y cliente PLAIN contra servidor TLS |
| `test_client_api_transport_errors.py` | Clasificacion de errores de transporte (`TLS_REQUIRED`) |
| `test_server_accept_error_filter.py` | Filtro de ruido transitorio (`WinError 10053/10054`) en `accept()` |
| `test_integration.py` | Ciclo completo: registro -> login -> TX -> logout |

## ðŸŽ¯ Modos de SimulaciÃ³n de Ataques

El cliente incluye modos interactivos para simular ataques:

### 1. Ataque Replay (OpciÃ³n 5)

EnvÃ­a el mismo mensaje dos veces para verificar que el servidor rechaza el segundo intento.

### 2. Ataque MITM (OpciÃ³n 6)

Modifica el payload despuÃ©s de calcular el MAC para verificar que el servidor detecta la manipulaciÃ³n.

## ðŸ“Š Logs y Evidencias

Los logs se generan en el directorio `logs/`:

- **`server.log`**: Eventos del servidor (registro, login, transacciones, ataques detectados)
- **`client.log`**: Eventos del cliente

### Eventos Registrados

**Servidor:**
- âœ… Usuario registrado
- âœ… Login exitoso / âŒ Login fallido
- âœ… TransacciÃ³n aceptada
- âŒ MAC invÃ¡lido detectado (MITM)
- âŒ Nonce repetido detectado (Replay)
- âŒ Rate limit activado (Brute force)

**Seguridad de Logs:**
- **NO** se vuelcan secretos completos (claves, MACs, passwords)
- Secretos se truncan: `abc123...` (solo primeros 8 caracteres)

## ðŸ› ï¸ ConfiguraciÃ³n

### Variables de Entorno (Opcional)

Copiar archivos de ejemplo:
```powershell
Copy-Item .env.example .env
```

Variables disponibles:
```bash
# Red y transporte
SERVER_HOST=127.0.0.1
SERVER_PORT=9999
TRANSPORT_MODE=PLAIN

# TLS (si TRANSPORT_MODE=TLS)
TLS_CERT_FILE=config/tls/server.crt
TLS_KEY_FILE=config/tls/server.key
TLS_CA_FILE=config/tls/ca.crt
TLS_SERVER_HOSTNAME=localhost
TLS_MIN_VERSION=1.3

# Seguridad (misma en cliente y servidor)
MASTER_KEY=CHANGE_THIS_IN_PRODUCTION_USE_256_BIT_KEY_MINIMUM

# Logging
LOG_LEVEL=INFO
```

**âš ï¸ CRÃTICO**: En producciÃ³n, generar una `MASTER_KEY` segura:
```powershell
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

## ðŸ” Mitigaciones de Ataques

### Man-in-the-Middle (MITM)

**Ataque**: Atacante intercepta y modifica mensajes en trÃ¡nsito.

**MitigaciÃ³n**:
1. Cada mensaje incluye HMAC-SHA256 sobre todos los campos
2. El servidor recalcula el HMAC y verifica con `hmac.compare_digest()`
3. Si no coincide â†’ mensaje rechazado con cÃ³digo `INVALID_MAC`

### Replay Attack

**Ataque**: Atacante captura un mensaje legÃ­timo y lo reenvÃ­a.

**MitigaciÃ³n**:
1. Cada mensaje incluye un nonce Ãºnico (128 bits aleatorios)
2. El servidor almacena nonces usados en BD (tabla `nonces`)
3. Si el nonce ya existe â†’ mensaje rechazado con cÃ³digo `REPLAY_ATTACK`

### Timing Attack (Canal Lateral de Tiempo)

**Ataque**: Medir el tiempo de respuesta para inferir informaciÃ³n.

**MitigaciÃ³n**:
1. ComparaciÃ³n de MACs con `hmac.compare_digest()` (tiempo constante)
2. ComparaciÃ³n de passwords con `hmac.compare_digest()` (tiempo constante)

### Brute Force (AdivinaciÃ³n de Passwords)

**Ataque**: Probar mÃºltiples passwords hasta encontrar el correcto.

**MitigaciÃ³n**:
1. Rate limiting: mÃ¡ximo N intentos fallidos por usuario (default: 5)
2. Backoff exponencial: bloqueo de 2^n segundos tras exceder el lÃ­mite
3. Registro de intentos en BD para auditorÃ­a

## ðŸŽ“ Resumen TÃ©cnico

**ImplementaciÃ³n de:**
- âœ… ComunicaciÃ³n por sockets TCP (no HTTP)
- âœ… HMAC-SHA256 para integridad (claves 256 bits)
- âœ… Nonce Ãºnico + timestamp para anti-replay
- âœ… `hmac.compare_digest()` para anti-timing
- âœ… Rate limiting + backoff exponencial
- âœ… PBKDF2 (150k iter) para passwords
- âœ… HKDF para derivaciÃ³n de claves por usuario
- âœ… Persistencia SQLite (usuarios, transacciones, nonces, sesiones)
- âœ… Logs completos con eventos de seguridad
- ✅ Tests automatizados para criptografia, protocolo, rate limit y transporte TLS
- âœ… Modos de simulaciÃ³n de ataques (Replay, MITM)

**Ataques mitigados:**
- âœ… Man-in-the-Middle (HMAC)
- âœ… Replay (nonce store)
- âœ… Timing (comparaciones en tiempo constante)
- âœ… Brute Force (rate limiting)
- âœ… Key Derivation (claves >= 256 bits)

---

**Asignatura**: SSII - Seguridad en Sistemas InformÃ¡ticos  
**Fecha**: Febrero 2026






