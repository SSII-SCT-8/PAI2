"""
Compara dos resultados JSON de benchmark y genera resumen + tabla Markdown.

Ejemplo:
python scripts/compare_benchmark_results.py \
  --tls logs/benchmark_tls_run.json \
  --baseline logs/benchmark_pai1_run.json \
  --output-md docs/BENCHMARK_COMPARATIVA.md
"""
import argparse
import json
from pathlib import Path
from typing import Any, Dict, Optional


def _load_summary(path: Path) -> Dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if "summary" not in data:
        raise ValueError(f"Formato invalido en {path}: falta 'summary'")
    return data["summary"]


def _safe_get_duration(summary: Dict[str, Any], key: str) -> Optional[float]:
    duration = summary.get("duration_s") or {}
    value = duration.get(key)
    return float(value) if isinstance(value, (int, float)) else None


def _throughput(summary: Dict[str, Any]) -> Optional[float]:
    total_messages = summary.get("total_messages_sent")
    elapsed = summary.get("elapsed_total_s")
    if not isinstance(total_messages, (int, float)) or not isinstance(elapsed, (int, float)):
        return None
    if elapsed <= 0:
        return None
    return float(total_messages) / float(elapsed)


def _fmt(value: Optional[float], digits: int = 3) -> str:
    if value is None:
        return "N/A"
    return f"{value:.{digits}f}"


def _build_markdown(
    baseline_name: str,
    baseline: Dict[str, Any],
    tls_name: str,
    tls: Dict[str, Any],
) -> str:
    rows = [
        ("Clientes totales", baseline.get("total_clients"), tls.get("total_clients")),
        ("Clientes OK", baseline.get("ok_clients"), tls.get("ok_clients")),
        ("Clientes fallidos", baseline.get("failed_clients"), tls.get("failed_clients")),
        ("Mensajes/tx enviados", baseline.get("total_messages_sent"), tls.get("total_messages_sent")),
        ("Tiempo total (s)", _fmt(float(baseline.get("elapsed_total_s", 0.0))), _fmt(float(tls.get("elapsed_total_s", 0.0)))),
        ("Throughput (msg/s)", _fmt(_throughput(baseline)), _fmt(_throughput(tls))),
        ("Latencia avg cliente (s)", _fmt(_safe_get_duration(baseline, "avg")), _fmt(_safe_get_duration(tls, "avg"))),
        ("Latencia p95 cliente (s)", _fmt(_safe_get_duration(baseline, "p95")), _fmt(_safe_get_duration(tls, "p95"))),
    ]

    lines = [
        "# Comparativa de rendimiento: baseline vs TLS",
        "",
        f"- Baseline: `{baseline_name}`",
        f"- TLS: `{tls_name}`",
        "",
        "| Metrica | Baseline | TLS |",
        "|---|---:|---:|",
    ]
    for metric, b, t in rows:
        lines.append(f"| {metric} | {b} | {t} |")

    baseline_thr = _throughput(baseline)
    tls_thr = _throughput(tls)
    if baseline_thr and baseline_thr > 0 and tls_thr:
        delta = ((tls_thr - baseline_thr) / baseline_thr) * 100.0
        if delta >= 0:
            delta_line = f"- Variacion de throughput con TLS: `+{delta:.2f}%` (mejora frente al baseline)."
        else:
            delta_line = f"- Variacion de throughput con TLS: `{delta:.2f}%` (caida frente al baseline)."
        lines.extend(
            [
                "",
                "## Lectura rapida",
                "",
                delta_line,
                "- Interpreta esta variacion junto a las garantias de confidencialidad/autenticidad/integridad de TLS 1.3.",
            ]
        )

    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Compara resultados de benchmark JSON")
    parser.add_argument("--baseline", required=True, help="JSON benchmark baseline (ej. PAI1)")
    parser.add_argument("--tls", required=True, help="JSON benchmark TLS (ej. PAI2)")
    parser.add_argument("--baseline-name", default="PAI1 (sin TLS)")
    parser.add_argument("--tls-name", default="PAI2 (TLS 1.3)")
    parser.add_argument("--output-md", required=True, help="Ruta de salida markdown")
    args = parser.parse_args()

    baseline_path = Path(args.baseline)
    tls_path = Path(args.tls)
    output_md = Path(args.output_md)

    baseline_summary = _load_summary(baseline_path)
    tls_summary = _load_summary(tls_path)
    md = _build_markdown(args.baseline_name, baseline_summary, args.tls_name, tls_summary)

    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_md.write_text(md, encoding="utf-8")
    print(f"Comparativa generada en: {output_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
