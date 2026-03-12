# PAI2 - Road Warrior VPN SSL/TLS (TLS-only)

Este proyecto funciona **solo con TLS 1.3**.  
Se han retirado las capas de seguridad de aplicacion heredadas de PAI1:

- Sin `PLAIN`
- Sin `nonce`
- Sin `HMAC` por mensaje
- Sin derivacion de claves de mensaje

## Requisitos

- Python 3.10+
- Dependencias: `pip install -r requirements.txt`

## Configuracion rapida

1. Copiar `.env.example` a `.env`.
2. Verificar rutas TLS en `config/tls/`.
3. Inicializar BD:

```powershell
python config/seed_database.py
```

## Ejecucion

Servidor:

```powershell
python -m src.server.server
```

```bash
python -m src.server.server
```

Cliente:

```powershell
python -m src.client.client
```

```bash
python -m src.client.client
```

Demo automatizada (Windows):

```powershell
.\scripts\demo_run.ps1
```

Demo automatizada (Linux):

```bash
bash ./scripts/demo_run.sh
```

## Seguridad vigente

- TLS 1.3 obligatorio con validacion de certificado.
- Certificados TLS generados con ECC (ECDSA P-256 por defecto).
- Passwords almacenadas con `PBKDF2-HMAC-SHA256` + `salt` aleatorio (seguridad en reposo).
- Rate limiting y backoff exponencial para login.
- Gestion de sesiones con expiracion.

## Tests

```powershell
python -m unittest discover -s tests -p "test_*.py" -v
```

```bash
python -m unittest discover -s tests -p "test_*.py" -v
```

## Flujo funcional PAI2 (Integrante B)

- `TX` evoluciona a `MSG` con payload `{ "text": "..." }`.
- Validacion estricta de longitud: `1..144` caracteres (cliente y servidor).
- Persistencia en tabla `messages` (`username`, `message_text`, `ts`, `created_at`).
- Consulta de historial con `HISTORY` y `limit` opcional.
- Respuestas de error nuevas para mensajes: `EMPTY_MESSAGE`, `MSG_TOO_LONG`.

## Scripts Windows y Linux (equivalentes)

- Windows: `scripts/start_server.ps1`, `scripts/start_client.ps1`, `scripts/run_tests.ps1`, `scripts/demo_run.ps1`
- Linux: `scripts/start_server.sh`, `scripts/start_client.sh`, `scripts/run_tests.sh`, `scripts/demo_run.sh`
