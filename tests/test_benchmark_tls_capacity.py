"""Tests unitarios para el benchmark TLS de capacidad."""
import sys
import unittest
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scripts.benchmark_tls_capacity import _summarize


class TestBenchmarkTLSSummary(unittest.TestCase):
    """Valida el agregado de resultados del benchmark."""

    def test_summarize_counts_ok_and_errors(self):
        results = [
            {"ok": True, "duration_s": 0.2, "sent": 2},
            {"ok": True, "duration_s": 0.3, "sent": 2},
            {"ok": False, "error": "CONNECT_FAILED", "duration_s": 0.1},
            {"ok": False, "error": "CONNECT_FAILED", "duration_s": 0.1},
            {"ok": False, "error": "LOGIN_FAILED", "duration_s": 0.1},
        ]

        summary = _summarize(results)

        self.assertEqual(summary["total_clients"], 5)
        self.assertEqual(summary["ok_clients"], 2)
        self.assertEqual(summary["failed_clients"], 3)
        self.assertEqual(summary["total_messages_sent"], 4)
        self.assertEqual(summary["errors"]["CONNECT_FAILED"], 2)
        self.assertEqual(summary["errors"]["LOGIN_FAILED"], 1)
        self.assertIn("duration_s", summary)
        self.assertIsNotNone(summary["duration_s"]["avg"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
