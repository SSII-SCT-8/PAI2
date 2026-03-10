# Plan Equilibrado para 3 Integrantes (PAI2 BYODSEC en Python)

## Resumen
Objetivo: evolucionar la base previa para cumplir PAI2 con canal seguro TLS 1.3, envío de mensajes de texto (máx. 144), persistencia e historial, pruebas de confidencialidad/rendimiento y memoria técnica final.

Criterio de éxito del proyecto:
- Comunicación cliente-servidor cifrada con TLS 1.3 y autenticidad por certificado.
- Registro/login/logout funcionales con protección brute force y credenciales seguras.
- Envío de mensajes de texto con límite 144, persistencia, historial y contador por usuario.
- Evidencias de red (`.pcap`) mostrando diferencia entre canal plano y TLS.
- Prueba de carga a 300 concurrentes con comparativa sin TLS vs con TLS.
- Entregable final trazable (código, tests, logs, trazas, PDF <=10 páginas).

## Organización del trabajo (carga equilibrada)
Distribución por puntos de esfuerzo (equilibrada):
- Integrante A (Infra/TLS): 34 puntos.
- Integrante B (Lógica/Persistencia): 33 puntos.
- Integrante C (QA/Análisis/Documentación): 33 puntos.

Regla de coordinación:
- Cada tarea termina con evidencia mínima (test/log/captura).
- PR pequeño por bloque funcional.
- Nadie bloquea a otro más de medio día: si hay bloqueo, se crea fallback inmediato.

## Backlog detallado por integrante

### Integrante A: Infraestructura y Seguridad de Acceso (34 puntos)
- A1 (8): Migrar sockets TCP a TLS usando `ssl.SSLContext` en cliente/servidor.
- A2 (6): Forzar TLS 1.3 (`minimum_version=ssl.TLSVersion.TLSv1_3`) y deshabilitar negociación insegura.
- A3 (6): Configurar certificados y confianza (CA local + cert servidor + trust del cliente) con scripts reproducibles.
- A4 (4): Añadir modo dual de ejecución `PLAIN` y `TLS` por variable de entorno para comparativa de rendimiento.
- A5 (4): Endurecer configuración de transporte (timeouts, manejo de handshake fallido, errores claros).
- A6 (3): Mantener/ajustar controles de brute force y credenciales dentro del nuevo flujo TLS.
- A7 (3): Tests de transporte seguro (conexión válida, cert inválido, intento sin TLS contra servidor TLS).

### Integrante B: Lógica de Negocio y Persistencia (33 puntos)
- B1 (6): Sustituir modelo `TX` por `MSG` para PAI2 sin romper registro/login/logout.
- B2 (6): Implementar validación estricta de mensaje de texto `1..144` caracteres (cliente y servidor).
- B3 (7): Crear persistencia de mensajes (`messages`) con `username`, `message_text`, `ts`, `created_at`.
- B4 (5): Implementar historial de mensajes por usuario y contador total por usuario.
- B5 (4): Ajustar interfaz CLI/API para enviar mensaje y consultar historial.
- B6 (3): Actualizar semilla inicial para usuarios pre-registrados y sin mensajes previos.
- B7 (2): Mensajes de sistema alineados a requisito (“mensaje enviado/recibido correctamente”, errores de longitud, etc.).

### Integrante C: Analista de Seguridad, Rendimiento y Memoria (33 puntos)
- C1 (6): Diseñar matriz de trazabilidad requisito -> test/evidencia -> archivo.
- C2 (7): Capturas de tráfico con Wireshark/RawCap en modo PLAIN y TLS, con filtros y evidencia clara de confidencialidad.
- C3 (8): Diseñar y ejecutar prueba de carga de 300 concurrentes en ambos modos (PLAIN/TLS).
- C4 (5): Recoger métricas comparables: latencia media/p95, throughput, tasa de error, consumo CPU/memoria.
- C5 (5): Redactar memoria técnica final (<=10 páginas) con resultados reproducibles y conclusiones.
- C6 (2): Paquete de entrega: estructura final del zip y checklist de cumplimiento.

## Cambios de interfaces públicas (decision-complete)

- Protocolo de mensajes:
  - `type`: mantener `REGISTER`, `LOGIN`, `LOGOUT`; reemplazar `TX` por `MSG`; añadir `HISTORY` para consulta.
  - `payload` de `MSG`: `{ "text": "<string max 144>" }`.
  - `payload` de `HISTORY`: `{ "limit": <int opcional> }`.
- Respuestas servidor:
  - `RESPONSE` éxito con `success=true`, `message`, `data`.
  - `ERROR` con `success=false`, `code`, `message`.
  - Códigos nuevos mínimos: `MSG_TOO_LONG`, `EMPTY_MESSAGE`, `TLS_REQUIRED`, `TLS_HANDSHAKE_FAILED`.
- Configuración (`.env`):
  - `TRANSPORT_MODE=TLS|PLAIN`
  - `TLS_CERT_FILE`, `TLS_KEY_FILE`, `TLS_CA_FILE`
  - `TLS_MIN_VERSION=1.3`
- Persistencia:
  - Nueva tabla `messages`.
  - Consultas nuevas: insertar mensaje, listar historial por usuario, contar mensajes por usuario.

## Casos de prueba y escenarios

- Seguridad transporte:
  - Conexión TLS válida funciona.
  - Certificado no confiable falla.
  - Cliente en plano contra servidor TLS falla con error controlado.
- Funcionalidad:
  - Registro único, login correcto/incorrecto, logout.
  - Envío de mensaje válido (<=144) persiste correctamente.
  - Mensaje vacío y >144 rechazados.
  - Historial devuelve mensajes ordenados por fecha y contador correcto.
- Seguridad credenciales:
  - Password almacenada con hash seguro.
  - Brute force bloquea tras umbral.
- Rendimiento:
  - 300 usuarios concurrentes en PLAIN y TLS.
  - Comparativa de métricas con tabla final.
- Evidencia de red:
  - En PLAIN se puede inspeccionar contenido.
  - En TLS no se observa texto en claro del mensaje.

## Riesgos críticos y control

- Riesgo 1: TLS 1.3 no queda realmente forzado.
  - Control: test automático de versión negociada y rechazo de versiones inferiores.
- Riesgo 2: Certificados/trust mal montados en entornos distintos.
  - Control: scripts únicos y guía paso a paso reproducible.
- Riesgo 3: No alcanzar 300 concurrentes por cuellos en servidor/SQLite.
  - Control: ensayo incremental (50/100/200/300), ajuste de timeouts y estrategia de escrituras.
- Riesgo 4: Inconsistencia de validación 144 chars.
  - Control: validación duplicada cliente+servidor y tests de borde 143/144/145.
- Riesgo 5: Memoria final no trazable.
  - Control: matriz de trazabilidad mantenida desde el inicio por Integrante C.

## Suposiciones y decisiones por defecto
- Se implementa en Python (no Java, no `keytool`).
- El requisito de “VPN SSL” se cubre mediante canal TLS cliente-servidor con evidencias de confidencialidad, integridad y autenticidad.
- Se mantiene SQLite como base de datos.
- Se conserva la arquitectura actual cliente/servidor y se evoluciona, no se rehace desde cero.
- La comparación de rendimiento se hará con el mismo código en dos modos (`PLAIN` y `TLS`) para que la comparación sea justa.

## Estado de avance (Integrante A)

Actualizado: 2026-03-09

- A1: completado.
- A2: completado.
- A3: completado.
- A4: completado.
- A5: completado.
- A6: completado.
- A7: completado.

Evidencia detallada: `docs/INTEGRANTE_A_STATUS.md`.
