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

Cliente:

```powershell
python -m src.client.client
```

Demo automatizada (Windows):

```powershell
.\scripts\demo_run.ps1
```

## Seguridad vigente

- TLS 1.3 obligatorio con validacion de certificado.
- Passwords almacenadas con `PBKDF2-HMAC-SHA256` + `salt` aleatorio (seguridad en reposo).
- Rate limiting y backoff exponencial para login.
- Gestion de sesiones con expiracion.

## Tests

```powershell
python -m unittest discover -s tests -p "test_*.py" -v
```
