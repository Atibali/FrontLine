"""Hybrid routing between the offline rules engine and Groq."""

from __future__ import annotations

from .groq_client import GroqClient, GroqClientError
from .triage import triage_message


_PRIORITY_ORDER = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}


def triage_hybrid(message: str | None, message_id: str | None = None, *, groq_client: GroqClient | None = None) -> dict:
    offline = triage_message(message, message_id)
    if groq_client is None:
        return offline

    # Never send injection, empty, or unclassifiable messages to Groq.
    # The offline engine returns confidence=0.0 for these cases.
    if offline.get("confidence", 1.0) == 0.0:
        return offline

    if not _should_call_groq(offline):
        return offline

    try:
        remote = groq_client.triage("" if message is None else str(message))
    except GroqClientError:
        return offline

    return _merge_decisions(offline, remote)


def _should_call_groq(offline: dict) -> bool:
    return bool(
        offline.get("needs_human")
        or offline.get("confidence", 0.0) < 0.7
        or offline.get("category") in {"unknown", "complaint"}
    )


def _merge_decisions(offline: dict, remote: dict) -> dict:
    merged = dict(offline)

    remote_category = remote.get("category", "unknown")
    remote_confidence = float(remote.get("confidence", 0.05))
    remote_priority = str(remote.get("priority", "P3"))

    if remote_category == offline.get("category"):
        merged["priority"] = _more_urgent_priority(str(offline.get("priority", "P3")), remote_priority)
        merged["needs_human"] = bool(offline.get("needs_human", True) or remote.get("needs_human", True))
        merged["confidence"] = max(float(offline.get("confidence", 0.0)), remote_confidence)
        return merged

    if offline.get("category") == "unknown" and remote_category != "unknown" and remote_confidence >= 0.80:
        merged.update(remote)
        merged["needs_human"] = True
        merged["confidence"] = max(float(offline.get("confidence", 0.0)), remote_confidence)
        return merged

    if remote.get("needs_human"):
        merged["needs_human"] = True
    merged["confidence"] = min(float(offline.get("confidence", 0.0)), remote_confidence)
    return merged


def _more_urgent_priority(left: str, right: str) -> str:
    if _PRIORITY_ORDER.get(right, 3) < _PRIORITY_ORDER.get(left, 3):
        return right
    return left
