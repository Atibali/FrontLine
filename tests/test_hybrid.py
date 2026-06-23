"""Hybrid Groq tests."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from frontline.groq_client import GroqClientError, _normalize_decision
from frontline.hybrid import triage_hybrid


class FakeGroqClient:
    def triage(self, message: str) -> dict:
        return {
            "category": "billing",
            "priority": "P2",
            "summary": "billing issue",
            "suggested_action": "Review billing records.",
            "needs_human": False,
            "confidence": 0.9,
        }


class FailingGroqClient:
    def triage(self, message: str) -> dict:
        raise GroqClientError("boom")


class HybridTests(unittest.TestCase):
    def test_normalize_decision_enforces_contract(self):
        decision = _normalize_decision(
            json.dumps(
                {
                    "category": "billing",
                    "priority": "P2",
                    "summary": "billing issue",
                    "suggested_action": "Review billing records.",
                    "needs_human": False,
                    "confidence": 0.9,
                }
            )
        )
        self.assertEqual(set(decision), {"category", "priority", "summary", "suggested_action", "needs_human", "confidence"})

    def test_hybrid_falls_back_to_offline_when_no_client(self):
        decision = triage_hybrid("help", "x", groq_client=None)
        self.assertEqual(set(decision), {"category", "priority", "summary", "suggested_action", "needs_human", "confidence"})

    def test_hybrid_merges_remote_result(self):
        decision = triage_hybrid("I was charged twice.", "x", groq_client=FakeGroqClient())
        self.assertEqual(decision["category"], "billing")
        self.assertEqual(set(decision), {"category", "priority", "summary", "suggested_action", "needs_human", "confidence"})

    def test_hybrid_falls_back_when_remote_fails(self):
        decision = triage_hybrid("I was charged twice.", "x", groq_client=FailingGroqClient())
        self.assertEqual(set(decision), {"category", "priority", "summary", "suggested_action", "needs_human", "confidence"})


if __name__ == "__main__":
    unittest.main()
