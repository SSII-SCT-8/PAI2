# Comparativa de rendimiento: baseline vs TLS

- Baseline: `PAI1 (sin TLS)`
- TLS: `PAI2 (TLS 1.3)`

| Metrica | Baseline | TLS |
|---|---:|---:|
| Clientes totales | 300 | 300 |
| Clientes OK | 231 | 262 |
| Clientes fallidos | 69 | 38 |
| Mensajes/tx enviados | 462 | 524 |
| Tiempo total (s) | 61.734 | 38.080 |
| Throughput (msg/s) | 7.484 | 13.761 |
| Latencia avg cliente (s) | 13.439 | 7.786 |
| Latencia p95 cliente (s) | 31.763 | 21.852 |

## Lectura rapida

- Variacion de throughput con TLS: `+83.87%` (mejora frente al baseline).
- Interpreta esta variacion junto a las garantias de confidencialidad/autenticidad/integridad de TLS 1.3.
