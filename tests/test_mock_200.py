from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from frontline.io import read_jsonl
from frontline.triage import REQUIRED_FIELDS, triage_message


class Mock200Tests(unittest.TestCase):
    def test_mock_200_dataset_exists_and_runs(self):
        rows = read_jsonl(ROOT / "data" / "mock_200.jsonl")
        self.assertEqual(len(rows), 200)
        for row in rows:
            decision = triage_message(row.get("message"), row.get("id"))
            self.assertEqual(set(decision), set(REQUIRED_FIELDS))
            self.assertIn(decision["priority"], {"P0", "P1", "P2", "P3"})


if __name__ == "__main__":
    unittest.main()
