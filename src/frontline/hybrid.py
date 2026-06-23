"""Hybrid routing between the offline rules engine and Groq."""

from __future__ import annotations

from .groq_client import GroqClient, GroqClientError
from .triage import triage_message


def triage_hybrid(message: str | None, message_id: str | None = None, *, groq_client: GroqClient | None = None) -> dict:
    offline = triage_message(message, message_id)
    if groq_client is None:
        return offline

    if not _should_call_groq(offline):
        return offline

    try:
        remote = groq_client.triage("" if message is None else str(message))
    except GroqClientError:
        return offline

    merged = dict(offline)
    merged.update(remote)
    merged["needs_human"] = bool(offline["needs_human"] or remote.get("needs_human", True))
    merged["confidence"] = min(float(offline["confidence"]), float(remote.get("confidence", 0.05)))
    return merged


def _should_call_groq(offline: dict) -> bool:
    return bool(
        offline.get("needs_human")
        or offline.get("confidence", 0.0) < 0.7
        or offline.get("category") in {"unknown", "complaint"}
    )
