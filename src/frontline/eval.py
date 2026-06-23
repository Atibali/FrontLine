"""Simple agreement metrics for hand-labeled examples."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EvaluationResult:
    total: int
    category_accuracy: float
    priority_accuracy: float
    human_accuracy: float
    exact_accuracy: float
    failures: list[dict]


def evaluate(truth: list[dict], predictions: list[dict], source_rows: list[dict] | None = None) -> EvaluationResult:
    by_id = {str(row.get("id")): row for row in predictions if row.get("id") is not None}
    if not by_id and source_rows is not None:
        by_id = {
            str(source_row.get("id")): prediction
            for source_row, prediction in zip(source_rows, predictions)
            if source_row.get("id") is not None
        }

    total = len(truth)
    category_hits = 0
    priority_hits = 0
    human_hits = 0
    exact_hits = 0
    failures: list[dict] = []

    for expected in truth:
        item_id = str(expected.get("id"))
        actual = by_id.get(item_id)
        if actual is None:
            failures.append({"id": item_id, "reason": "missing prediction"})
            continue

        category_ok = actual.get("category") == expected.get("category")
        priority_ok = actual.get("priority") == expected.get("priority")
        human_ok = actual.get("needs_human") == expected.get("needs_human")
        category_hits += int(category_ok)
        priority_hits += int(priority_ok)
        human_hits += int(human_ok)
        exact_hits += int(category_ok and priority_ok and human_ok)
        if not (category_ok and priority_ok and human_ok):
            failures.append(
                {
                    "id": item_id,
                    "expected": {
                        "category": expected.get("category"),
                        "priority": expected.get("priority"),
                        "needs_human": expected.get("needs_human"),
                    },
                    "actual": {
                        "category": actual.get("category"),
                        "priority": actual.get("priority"),
                        "needs_human": actual.get("needs_human"),
                    },
                }
            )

    denominator = total or 1
    return EvaluationResult(
        total=total,
        category_accuracy=category_hits / denominator,
        priority_accuracy=priority_hits / denominator,
        human_accuracy=human_hits / denominator,
        exact_accuracy=exact_hits / denominator,
        failures=failures,
    )
