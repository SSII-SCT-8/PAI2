# PAI-2 BYODSEC - Memoria de Entrega (analisis actualizado)

## 1. Resumen de decisiones tecnicas y algoritmicas

### 1.1 Alcance implementado

El proyecto esta implementado como arquitectura cliente-servidor en Python con canal TLS 1.3 obligatorio.

Decisiones principales:

1. Transporte seguro exclusivamente con TLS 1.3.
2. Eliminacion de mecanismos de aplicacion legacy (`nonce`, `HMAC`, modo plano), delegando confidencialidad, autenticidad e integridad en TLS.
3. Credenciales en reposo con `PBKDF2-HMAC-SHA256` + `salt` aleatorio por usuario.
4. Modelo funcional actualizado a mensajes de texto:
   - `MSG` para envio de mensajes.
   - `HISTORY` para consulta de historial.
   - compatibilidad legacy `TX` transformada a `MSG`.
5. Persistencia SQLite con tablas de `users`, `sessions`, `messages`, `login_attempts` y compatibilidad historica.
6. Mitigacion de brute force en login con rate limit + backoff exponencial.

Referencias de implementacion:

- Transporte TLS: `src/common/transport.py`.
- Parametros TLS: `src/server/config.py` (`TLS_MIN_VERSION=1.3`, `TLS_ECDH_CURVE=prime256v1`).
- Modelo de mensajes (1..144): `src/common/models.py`.
- Handlers de `MSG`/`HISTORY`: `src/server/handlers.py`.
- Persistencia de mensajes: `src/server/storage.py`.
- API cliente de mensajes: `src/client/api.py`.

### 1.2 Seguridad aplicada

1. **Confidencialidad del canal**: TLS 1.3 obligatorio.
2. **Autenticidad del servidor**: validacion de certificado en cliente.
3. **Integridad del canal**: garantizada por TLS 1.3.
4. **Credenciales seguras en BD**: hash PBKDF2 con iteraciones endurecidas.
5. **Proteccion en login**: bloqueo por intentos fallidos y backoff.
6. **Sesion**: creacion, expiracion e invalidacion por logout.

### 1.3 Evidencia de pruebas

Ejecucion local de test realizada el **16/03/2026**:

- Comando: `python -m unittest discover -s tests -p "test_*.py" -v`
- Resultado: **46 tests ejecutados, 46 OK**

Coberturas destacables:

1. Flujo completo registro/login/msg/history/logout (`tests/test_integration.py`).
2. Validacion de longitud 1..144 y errores `EMPTY_MESSAGE`/`MSG_TOO_LONG` (`tests/test_messages.py`, `tests/test_cliente.py`).
3. Seguridad de login (`tests/test_security.py`, `tests/test_rate_limit.py`).
4. Transporte TLS y rechazo de CA invalida (`tests/test_tls_transport_integration.py`, `tests/test_transport_tls.py`).
5. Generacion de certificados ECC/RSA (`tests/test_tls_cert_generation.py`).

## 2. Manual de despliegue y uso (Linux)

### 2.1 Requisitos

1. Linux (Ubuntu/Debian/Fedora o similar).
2. Python 3.10 o superior.
3. `pip`.
4. Opcional para capturas: `tcpdump` y `tshark`.

### 2.2 Preparacion

Desde raiz del repo:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
cp .env.example .env
```

### 2.3 Certificados TLS

ECC por defecto:

```bash
python scripts/generate_tls_certs.py --force
```

RSA opcional:

```bash
python scripts/generate_tls_certs.py --algorithm rsa --force
```

### 2.4 Inicializar datos

```bash
python config/seed_database.py
```

Usuarios semilla (`config/seed_users.json`):

1. `alice / AliceSecure2024!`
2. `bob / BobPassword123#`
3. `admin / AdminPass2024$`

### 2.5 Ejecucion manual

Terminal 1:

```bash
source .venv/bin/activate
python -m src.server.server
```

Terminal 2:

```bash
source .venv/bin/activate
python -m src.client.client
```

### 2.6 Ejecucion con scripts Linux

```bash
chmod +x scripts/*.sh
./scripts/start_server.sh
./scripts/start_client.sh
./scripts/run_tests.sh
./scripts/demo_run.sh
```

### 2.7 Verificacion de canal cifrado (sniffer)

Captura:

```bash
sudo tcpdump -i lo -nn -s0 -w logs/tls_capture.pcap tcp port 9999
```

Inspeccion:

```bash
tshark -r logs/tls_capture.pcap -Y "tls" -T fields -e frame.number -e ip.src -e ip.dst -e tls.record.version
```

Criterio esperado:

1. Se observa handshake TLS.
2. No se observan credenciales ni contenido de mensaje en claro.

## 3. Grado de completitud (trazable)

### 3.1 Objetivos globales

| Objetivo | Estado | Evidencia | Comentario |
|---|---|---|---|
| Canal seguro para credenciales y mensajes con SSL/TLS | **Cumplido** | `src/common/transport.py`, `src/client/api.py`, `src/server/server.py` | TLS 1.3 forzado cliente/servidor |
| Cipher suites robustos con TLS 1.3 | **Parcial** | `TLS_MIN_VERSION=1.3`, `TLS_ECDH_CURVE=prime256v1` en `src/server/config.py` | Hay endurecimiento de version/curva; no hay fijacion explicita de ciphersuite |
| Analisis de trafico para verificar canal seguro | **Parcial** | Procedimiento en esta memoria | Falta adjuntar trazas `.pcap` y analisis en el zip |
| Soportar ~300 empleados concurrentes | **No cumplido** | `MAX_CONNECTIONS = 100` en `src/server/config.py` | Limite actual inferior al objetivo |
| Analisis de rendimiento y escalabilidad con/sin SSL/TLS | **No cumplido** | No hay benchmark en repo | Faltan pruebas de carga y comparativa |
| Extra MitM activo (opcional) | **Parcial (opcional)** | rechazo de CA invalida en `tests/test_tls_transport_integration.py` | No hay memoria de ataque MitM completo |

### 3.2 Requisitos funcionales

| Requisito funcional | Estado | Evidencia | Comentario |
|---|---|---|---|
| Registro de usuarios (usuario+contrasena) | **Cumplido** | `handle_register` en `src/server/handlers.py` | |
| Aviso si usuario ya existe | **Cumplido** | `user_exists` + respuesta de error | |
| No modificar datos tras registro | **Cumplido (sin endpoint de edicion)** | No hay API de actualizacion de usuario | |
| Inicio de sesion | **Cumplido** | `handle_login` / `ClientAPI.login` | |
| Verificar credenciales y denegar invalidas | **Cumplido** | `verify_password` en `src/common/crypto.py` | |
| Cerrar sesion | **Cumplido** | `handle_logout` / `ClientAPI.logout` | |
| Usuarios preexistentes | **Cumplido** | `config/seed_users.json`, `config/seed_database.py` | |
| Envio de mensajes de texto al servidor | **Cumplido** | `MSG` en `src/server/server.py` + `handle_message` | 1..144 caracteres |
| Persistencia de usuarios | **Cumplido** | tabla `users` en `src/server/storage.py` | |
| Persistencia de mensajes + numero por usuario | **Cumplido** | tabla `messages`, `count_user_messages`, `HISTORY` | Se guarda mensaje y total por usuario |
| Interfaz por sockets seguros | **Cumplido** | `src/common/protocol.py` + TLS | |

### 3.3 Requisitos de informacion

| Requisito de informacion | Estado | Evidencia | Comentario |
|---|---|---|---|
| Usuario unico y contrasena | **Cumplido** | `username` unico en tabla `users` | Password en hash+salt |
| BD inicial con usuarios pre-registrados y sin mensajes previos | **Parcial** | `seed_users.json` y `seed_database.py` | Cumple en BD nueva; si no se limpia BD, puede haber mensajes previos |
| Historial de mensajes con numero y fecha | **Cumplido** | `get_user_message_history`, `count_user_messages`, campos `ts/created_at` | |
| Envio incluye usuario + texto max 144 | **Cumplido** | `MESSAGE_MAX_LENGTH=144`, validacion cliente/servidor y `CHECK` SQL | |
| Mensajes de sistema (registro/login/envio) | **Cumplido** | respuestas en handlers y API | |

### 3.4 Requisitos de seguridad

| Requisito de seguridad | Estado | Evidencia | Comentario |
|---|---|---|---|
| Almacenamiento seguro de credenciales | **Cumplido** | `PBKDF2-HMAC-SHA256` en `src/common/crypto.py` | |
| Verificacion segura de credenciales | **Cumplido** | `verify_password` + `compare_digest` | |
| Proteccion frente a brute force | **Cumplido** | `SecurityManager.check_rate_limit` | |
| Integridad/confidencialidad/autenticidad en envio | **Cumplido** | TLS 1.3 obligatorio | |
| Integridad de datos en BD | **Parcial** | restricciones SQL + flujo controlado | No hay firma/MAC en reposo ni controles de auditoria avanzados |

## 4. Riesgos abiertos y acciones recomendadas

Prioridad alta:

1. Ajustar arquitectura de concurrencia para aproximar objetivo de 300 sesiones simultaneas.
2. Ejecutar y documentar benchmark de rendimiento/escalabilidad con metrica objetiva.
3. Adjuntar evidencias de sniffing (`.pcap` + capturas + interpretacion) en el entregable final.

Prioridad media:

1. Limpiar nomenclatura legacy (`TX`, `transactions`) cuando ya no se necesite compatibilidad.
2. Afinar validaciones y trazabilidad de auditoria (por ejemplo, eventos de seguridad estructurados).

Prioridad baja (extra):

1. Documentar prueba MitM activa controlada con metodologia y resultado.

## 5. Empaquetado de entrega (zip)

Contenido minimo recomendado de `PAI2-STX.zip`:

1. Codigo fuente.
2. Tests y salida de ejecucion.
3. Logs de servidor/cliente.
4. Trazas de sniffer y resumen.
5. Memoria PDF.

Comando Linux:

```bash
zip -r PAI2-STX.zip src config scripts tests docs logs readme.md requirements.txt .env.example
```

Conversion a PDF:

```bash
pandoc docs/PAI2_MEMORIA_ENTREGA.md -o docs/PAI2_MEMORIA_ENTREGA.pdf
```
