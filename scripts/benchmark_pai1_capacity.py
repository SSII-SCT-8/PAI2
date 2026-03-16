"""
Benchmark de capacidad/concurrencia para PAI1 (baseline sin TLS).

Ejemplo:
python scripts/benchmark_pai1_capacity.py --pai1-root ..\\PAI1 --clients 300 --messages-per-client 3
"""
import argparse
import json
import statistics
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, Any, List


def _load_pai1_client_api(pai1_root: Path):
    if not pai1_root.exists():
        raise FileNotFoundError(f"No existe ruta PAI1: {pai1_root}")
    sys.path.insert(0, str(pai1_root))
    from src.client.api import ClientAPI  # type: ignore
    return ClientAPI


def _run_virtual_user(
    idx: int,
    host: str,
    port: int,
    username_prefix: str,
    password: str,
    messages_per_client: int,
    client_api_cls,
) -> Dict[str, Any]:
    start = time.perf_counter()
    username = f"{username_prefix}_{idx}_{uuid.uuid4().hex[:8]}"
    client = client_api_cls(host=host, port=port)

    try:
        if not client.connect():
            return {
                "ok": False,
                "error": "CONNECT_FAILED",
                "detail": getattr(client, "last_connect_error_code", None),
                "duration_s": time.perf_counter() - start,
            }

        reg = client.register(username, password)
        if not reg.get("success"):
            return {
                "ok": False,
                "error": "REGISTER_FAILED",
                "detail": reg.get("message"),
                "duration_s": time.perf_counter() - start,
            }

        login = client.login(username, password)
        if not login.get("success"):
            return {
                "ok": False,
                "error": "LOGIN_FAILED",
                "detail": login.get("message"),
                "duration_s": time.perf_counter() - start,
            }

        sent = 0
        for i in range(messages_per_client):
            tx = client.send_transaction("ES1111", "ES2222", f"{100 + i}.00")
            if not tx.get("success"):
                return {
                    "ok": False,
                    "error": "TX_FAILED",
                    "detail": tx.get("message"),
                    "duration_s": time.perf_counter() - start,
                    "sent": sent,
                }
            sent += 1

        _ = client.logout()
        return {
            "ok": True,
            "duration_s": time.perf_counter() - start,
            "sent": sent,
        }
    finally:
        try:
            client.disconnect()
        except Exception:
            pass


def _summarize(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    total = len(results)
    ok_results = [r for r in results if r.get("ok")]
    fail_results = [r for r in results if not r.get("ok")]

    durations = [r["duration_s"] for r in ok_results]
    total_sent = sum(r.get("sent", 0) for r in ok_results)

    summary: Dict[str, Any] = {
        "total_clients": total,
        "ok_clients": len(ok_results),
        "failed_clients": len(fail_results),
        "total_messages_sent": total_sent,
        "errors": {},
    }

    if durations:
        summary["duration_s"] = {
            "min": min(durations),
            "max": max(durations),
            "avg": statistics.mean(durations),
            "p50": statistics.median(durations),
            "p95": statistics.quantiles(durations, n=100)[94] if len(durations) >= 20 else None,
        }

    for item in fail_results:
        code = item.get("error", "UNKNOWN_ERROR")
        summary["errors"][code] = summary["errors"].get(code, 0) + 1

    return summary


def main() -> int:
    project_root = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser(description="Benchmark baseline PAI1 sin TLS")
    parser.add_argument("--pai1-root", default=str(project_root.parent / "PAI1"))
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=9999)
    parser.add_argument("--clients", type=int, default=100)
    parser.add_argument("--workers", type=int, default=50)
    parser.add_argument("--messages-per-client", type=int, default=1)
    parser.add_argument("--username-prefix", default="bench_pai1")
    parser.add_argument("--password", default="BenchPassword2026!")
    parser.add_argument(
        "--output",
        default=str(project_root / "logs" / f"benchmark_pai1_{int(time.time())}.json"),
    )
    args = parser.parse_args()

    client_api_cls = _load_pai1_client_api(Path(args.pai1_root).resolve())

    overall_start = time.perf_counter()
    results: List[Dict[str, Any]] = []

    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = [
            executor.submit(
                _run_virtual_user,
                i,
                args.host,
                args.port,
                args.username_prefix,
                args.password,
                args.messages_per_client,
                client_api_cls,
            )
            for i in range(args.clients)
        ]
        for future in as_completed(futures):
            results.append(future.result())

    summary = _summarize(results)
    summary["elapsed_total_s"] = time.perf_counter() - overall_start

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps({"summary": summary, "results": results}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print("=" * 70)
    print("BENCHMARK BASELINE PAI1 (SIN TLS)")
    print("=" * 70)
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    print(f"\nResultados completos: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
