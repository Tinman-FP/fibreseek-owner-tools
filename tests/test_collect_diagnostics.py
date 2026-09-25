#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "collect_diagnostics.py"
SPEC = importlib.util.spec_from_file_location("collect_diagnostics", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class RedactionTests(unittest.TestCase):
    def test_text_redaction(self) -> None:
        text = "host 192.168.50.113 mac aa:bb:cc:dd:ee:ff user@example.com"
        result = MODULE.redact_text(text)
        self.assertNotIn("192.168.50.113", result)
        self.assertNotIn("aa:bb:cc:dd:ee:ff", result)
        self.assertNotIn("user@example.com", result)

    def test_structured_redaction(self) -> None:
        value = {
            "machine_id": "secret-id",
            "nested": {"serial_num": "secret-serial", "state": "ready"},
        }
        result = MODULE.redact_json(value)
        self.assertEqual(result["machine_id"], "<redacted>")
        self.assertEqual(result["nested"]["serial_num"], "<redacted>")
        self.assertEqual(result["nested"]["state"], "ready")

    def test_latest_touchscreen_log(self) -> None:
        entries = [
            {"path": "print_logs/anisotouch_2026-09-20.log", "modified": 20},
            {"path": "print_logs/anisotouch_2026-09-21.log", "modified": 30},
            {"path": "klippy.log", "modified": 40},
        ]
        self.assertEqual(
            MODULE.latest_touchscreen_log(entries),
            "print_logs/anisotouch_2026-09-21.log",
        )


if __name__ == "__main__":
    unittest.main()
