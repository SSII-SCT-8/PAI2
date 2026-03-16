"""
Orquesta benchmark comparativo PAI1 (sin TLS) vs PAI2 (TLS 1.3).

Ejemplo:
python scripts/run_benchmark_pai1_vs_pai2.py --clients 200 --workers 80 --messages-per-client 2
"""
import argparse
import os
import socket
import subprocess
import sys
import time
from pathlib import Path


def _wait_port(
    host: str,
    port: int,
    timeout_s: float = 15.0,
    process: subprocess.Popen | None = None,
) -> None:
    deadline = time.time() + timeout_s
    last_error = None
    while time.time() < deadline:
        if process is not None and process.poll() is not None:
            raise RuntimeError(
                f"Proceso de servidor terminó antes de abrir puerto {host}:{port} "
                f"(exit={process.returncode})"
            )
        try:
            with socket.create_connection((host, port), timeout=1.0):
                return
        except Exception as exc:
            last_error = exc
            time.sleep(0.2)
    raise RuntimeError(f"No se pudo abrir {host}:{port}: {last_error}")


def _run_cmd(cmd, cwd: Path, env=None) -> None:
    result = subprocess.run(cmd, cwd=cwd, env=env, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"Comando fallido ({result.returncode}): {' '.join(cmd)}")


def main() -> int:
    project_root = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser(description="Benchmark comparativo PAI1 vs PAI2")
    parser.add_argument("--pai1-root", default=str(project_root.parent / "PAI1"))
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port-pai1", type=int, default=9998)
    parser.add_argument("--port-pai2", type=int, default=9999)
    parser.add_argument("--clients", type=int, default=100)
    parser.add_argument("--workers", type=int, default=50)
    parser.add_argument("--messages-per-client", type=int, default=1)
    args = parser.parse_args()

    pai1_root = Path(args.pai1_root).resolve()
    logs_dir = project_root / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    pai1_db = pai1_root / "data" / "server.db"

    pai1_json = logs_dir / f"benchmark_pai1_run_{int(time.time())}.json"
    pai2_json = logs_dir / f"benchmark_pai2_run_{int(time.time())}.json"
    compare_md = project_root / "docs" / "BENCHMARK_COMPARATIVA.md"

    py = sys.executable

    # PAI1 baseline
    if pai1_db.exists():
        pai1_db.unlink()

    env1 = os.environ.copy()
    env1["SERVER_HOST"] = args.host
    env1["SERVER_PORT"] = str(args.port_pai1)
    log1 = logs_dir / "benchmark_server_pai1.log"
    log1_fp = log1.open("w", encoding="utf-8")
    server1 = subprocess.Popen(
        [py, "-m", "src.server.server"],
        cwd=pai1_root,
        env=env1,
        stdout=log1_fp,
        stderr=subprocess.STDOUT,
    )
    try:
        _wait_port(args.host, args.port_pai1, process=server1)
        _run_cmd(
            [
                py,
                "scripts/benchmark_pai1_capacity.py",
                "--pai1-root",
                str(pai1_root),
                "--host",
                args.host,
                "--port",
                str(args.port_pai1),
                "--clients",
                str(args.clients),
                "--workers",
                str(args.workers),
                "--messages-per-client",
                str(args.messages_per_client),
                "--output",
                str(pai1_json),
            ],
            cwd=project_root,
        )
    finally:
        server1.terminate()
        try:
            server1.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server1.kill()
        log1_fp.close()

    # PAI2 TLS
    env2 = os.environ.copy()
    env2["SERVER_HOST"] = args.host
    env2["SERVER_PORT"] = str(args.port_pai2)
    log2 = logs_dir / "benchmark_server_pai2.log"
    log2_fp = log2.open("w", encoding="utf-8")
    server2 = subprocess.Popen(
        [py, "-m", "src.server.server"],
        cwd=project_root,
        env=env2,
        stdout=log2_fp,
        stderr=subprocess.STDOUT,
    )
    try:
        _wait_port(args.host, args.port_pai2, process=server2)
        _run_cmd(
            [
                py,
                "scripts/benchmark_tls_capacity.py",
                "--host",
                args.host,
                "--port",
                str(args.port_pai2),
                "--clients",
                str(args.clients),
                "--workers",
                str(args.workers),
                "--messages-per-client",
                str(args.messages_per_client),
                "--output",
                str(pai2_json),
            ],
            cwd=project_root,
        )
    finally:
        server2.terminate()
        try:
            server2.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server2.kill()
        log2_fp.close()

    # Comparativa markdown
    _run_cmd(
        [
            py,
            "scripts/compare_benchmark_results.py",
            "--baseline",
            str(pai1_json),
            "--tls",
            str(pai2_json),
            "--output-md",
            str(compare_md),
        ],
        cwd=project_root,
    )

    print("\nResumen generado:")
    print(f"- Baseline PAI1: {pai1_json}")
    print(f"- TLS PAI2: {pai2_json}")
    print(f"- Comparativa MD: {compare_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
