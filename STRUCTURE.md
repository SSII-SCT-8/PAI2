# Estructura del Proyecto PAI2 (estado actual)

## Resumen

Proyecto cliente-servidor en Python para envio de mensajes y autenticacion sobre TLS 1.3.

Estado de seguridad actual:
- Transporte: TLS 1.3 obligatorio
- Sin capa legacy de aplicacion: no `PLAIN`, no `nonce`, no `HMAC` por mensaje
- Credenciales en reposo: PBKDF2-HMAC-SHA256 + salt aleatorio
- Proteccion de acceso: rate limiting + backoff + sesiones

## Arbol principal

```text
PAI2/
|-- src/
|   |-- common/
|   |   |-- crypto.py        # hashing de password y utilidades
|   |   |-- protocol.py      # framing TCP + serializacion
|   |   |-- models.py        # modelos de mensajes/respuestas
|   |   `-- errors.py        # excepciones de dominio
|   |-- server/
|   |   |-- server.py        # servidor TLS, loop de conexiones
|   |   |-- handlers.py      # REGISTER/LOGIN/TX/LOGOUT/PING
|   |   |-- storage.py       # SQLite (users, sessions, transactions, login_attempts)
|   |   |-- security.py      # rate limit y validacion de sesion
|   |   `-- config.py        # configuracion del servidor
|   `-- client/
|       |-- client.py        # CLI interactiva
|       |-- api.py           # API cliente-servidor
|       `-- config.py        # configuracion del cliente
|-- tests/                   # test_*.py (unit + integracion)
|-- scripts/                 # start_server, start_client, demo_run, run_tests
|-- config/                  # .env examples, seed_users, seed_database, tls/
|-- data/                    # sqlite y artefactos runtime
|-- logs/                    # logs runtime
|-- readme.md
|-- STRUCTURE.md
`-- PLAN.md
```

## Flujo funcional

1. `REGISTER`: crea usuario (password hasheada).
2. `LOGIN`: valida credenciales y crea sesion.
3. `TX`: registra transaccion (requiere sesion activa).
4. `LOGOUT`: invalida sesion.

## Persistencia (SQLite)

Tablas activas:
- `users`
- `sessions`
- `transactions`
- `login_attempts`

Compatibilidad:
- `storage.py` incluye compatibilidad con esquemas legacy de PAI1 para evitar roturas en BDs antiguas.

## Tests

Se ejecutan con:

```powershell
python -m unittest discover -s tests -p "test_*.py" -v
```

Cobertura actual:
- Transporte TLS (config y handshake)
- API cliente (errores y estado)
- Protocolo (framing/respuestas)
- Seguridad (rate limit/sesion)
- Integracion end-to-end
