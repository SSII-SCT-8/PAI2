# Plan PAI2 (actualizado a estado TLS-only)

## Objetivo

Mantener un cliente-servidor seguro para autenticacion y operaciones de negocio sobre TLS 1.3 obligatorio, con trazabilidad de pruebas y documentacion clara.

## Estado actual (2026-03-10)

Completado:
- Transporte TLS 1.3 en cliente y servidor.
- Validacion de certificados.
- Eliminacion de capas legacy de PAI1 en aplicacion (`PLAIN`, `nonce`, `HMAC` por mensaje).
- Password hashing seguro en BD (PBKDF2-HMAC-SHA256 + salt).
- Rate limiting y backoff para login.
- Gestion de sesiones.
- Suite de tests automatizada operativa.

Pendiente funcional de negocio (si aplica al alcance del equipo):
- Revisar migracion final `TX -> MSG`.
- Limite de longitud de mensaje y reglas de negocio definitivas.
- Historial/contador por usuario segun requisito final de entrega.

## Reglas de calidad

- Cada cambio con test asociado.
- Evitar texto ambiguo o desactualizado en docs.
- Mantener consistencia entre readme, scripts y configuracion `.env`.
- Evitar codificacion mixta: guardar archivos en UTF-8 limpio.

## Evidencia minima por bloque

- Codigo fuente actualizado.
- Tests en verde.
- Registro corto en `docs/INTEGRANTE_A_STATUS.md`.

## Comando estandar de verificacion

```powershell
python -m unittest discover -s tests -p "test_*.py" -v
```
