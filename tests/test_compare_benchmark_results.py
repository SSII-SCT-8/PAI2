"""Tests de utilidades de comparacion de benchmarks."""
import sys
import unittest
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scripts.compare_benchmark_results import _throughput, _build_markdown


class TestCompareBenchmarkResults(unittest.TestCase):
    """Valida calculos clave de comparativa."""

    def test_throughput_none_when_elapsed_invalid(self):
        self.assertIsNone(_throughput({"total_messages_sent": 10, "elapsed_total_s": 0}))
        self.assertIsNone(_throughput({"total_messages_sent": 10}))

    def test_build_markdown_contains_core_metrics(self):
        baseline = {
            "total_clients": 10,
            "ok_clients": 10,
            "failed_clients": 0,
            "total_messages_sent": 20,
            "elapsed_total_s": 2.0,
            "duration_s": {"avg": 0.2, "p95": 0.4},
        }
        tls = {
            "total_clients": 10,
            "ok_clients": 10,
            "failed_clients": 0,
            "total_messages_sent": 20,
            "elapsed_total_s": 2.5,
            "duration_s": {"avg": 0.25, "p95": 0.5},
        }
        md = _build_markdown("baseline", baseline, "tls", tls)
        self.assertIn("Comparativa de rendimiento", md)
        self.assertIn("Throughput (msg/s)", md)
        self.assertIn("Variacion de throughput con TLS", md)


if __name__ == "__main__":
    unittest.main(verbosity=2)
