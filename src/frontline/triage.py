"""Deterministic customer-message triage with conservative escalation.

The rules are intentionally transparent for a live challenge: every decision can
be defended without claiming the system knows facts that are not in the message.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable

VALID_PRIORITIES = ("P0", "P1", "P2", "P3")
VALID_CATEGORIES = (
    "billing",
    "technical_issue",
    "account_access",
    "security",
    "shipping",
    "complaint",
    "sales_question",
    "cancellation",
    "out_of_scope",
    "unknown",
)
REQUIRED_FIELDS = (
    "category",
    "priority",
    "summary",
    "suggested_action",
    "needs_human",
    "confidence",
)


@dataclass(frozen=True)
class CategoryRule:
    category: str
    keywords: tuple[str, ...]


CATEGORY_RULES = (
    CategoryRule(
        "security",
        (
            "hacked",
            "breach",
            "fraud",
            "stolen",
            "phishing",
            "unauthorized",
            "2fa",
            "two factor",
            "data leak",
            "account takeover",
            "strange login",
            "asked me for my password",
            "whatsapp",
        ),
    ),
    CategoryRule(
        "billing",
        (
            "charged",
            "charge",
            "refund",
            "invoice",
            "receipt",
            "payment",
            "billing",
            "billed",
            "card",
            "carte",
            "subscription",
            "double billed",
            "money",
            "paiement",
            "débitée",
            "debitada",
        ),
    ),
    CategoryRule(
        "account_access",
        (
            "login",
            "log in",
            "locked out",
            "password",
            "reset",
            "can't access",
            "cannot access",
            "verification code",
            "email changed",
            "entrar",
            "cuenta",
            "लॉगिन",
        ),
    ),
    CategoryRule(
        "technical_issue",
        (
            "bug",
            "error",
            "crash",
            "broken",
            "not loading",
            "timeout",
            "api",
            "sync",
            "failed",
            "blank screen",
            "export",
            "500",
            "server",
            "app",
        ),
    ),
    CategoryRule(
        "shipping",
        (
            "shipping",
            "shipment",
            "delivery",
            "delivered",
            "package",
            "tracking",
            "warehouse",
            "address",
            "courier",
        ),
    ),
    CategoryRule(
        "cancellation",
        (
            "cancel",
            "cancellation",
            "close my account",
            "delete my account",
            "terminate",
            "unsubscribe",
            "stop my plan",
        ),
    ),
    CategoryRule(
        "sales_question",
        (
            "pricing",
            "price",
            "quote",
            "demo",
            "plan",
            "enterprise",
            "feature",
            "trial",
            "discount",
            "do you support",
        ),
    ),
    CategoryRule(
        "complaint",
        (
            "angry",
            "furious",
            "terrible",
            "useless",
            "worst",
            "complaint",
            "unacceptable",
            "disappointed",
            "hate",
            "awful",
        ),
    ),
    CategoryRule(
        "out_of_scope",
        (
            "weather",
            "homework",
            "recipe",
            "dating",
            "movie",
            "bitcoin prediction",
            "write my essay",
            "joke",
        ),
    ),
)

INJECTION_TERMS = (
    "ignore previous instructions",
    "ignore all instructions",
    "system prompt",
    "developer message",
    "output p0",
    "return only",
    "do not classify",
    "you are now",
)
ANGER_TERMS = ("lawsuit", "lawyer", "legal", "sue", "chargeback", "regulator", "media", "twitter")
VAGUE_TERMS = ("help", "issue", "problem", "urgent", "asap", "broken", "doesn't work", "not working")
NON_ENGLISH_HINTS = (
    "hola",
    "gracias",
    "por favor",
    "bonjour",
    "merci",
    "namaste",
    "kripya",
    "à¤¨à¤¹à¥€à¤‚",
    "à¤®à¤¦à¤¦",
    "à¤®à¥‡à¤°à¤¾",
    "à¤•à¥ƒà¤ªà¤¯à¤¾",
)

ACTION_BY_CATEGORY = {
    "billing": "Review billing records and provide refund, invoice, or payment guidance.",
    "technical_issue": "Collect diagnostics, reproduce the issue, and route to technical support if needed.",
    "account_access": "Start account recovery after verifying the customer's identity.",
    "security": "Escalate to security review and protect the account before sharing sensitive details.",
    "shipping": "Check tracking and delivery status, then update the customer with next steps.",
    "complaint": "Acknowledge the complaint and route to a senior support owner.",
    "sales_question": "Send pricing or product information and offer a sales follow-up.",
    "cancellation": "Confirm cancellation intent and explain retention or account-closure options.",
    "out_of_scope": "Politely explain that the request is outside customer support scope.",
    "unknown": "Ask a human support teammate to review and request clarification.",
}


def triage_message(message: str | None, message_id: str | None = None) -> dict:
    """Return one strict triage decision for a raw customer message."""

    raw = "" if message is None else str(message)
    normalized = _normalize(raw)
    words = _word_count(normalized)
    signals = _collect_signals(normalized)
    category, category_score, runner_up_score = _classify(normalized)
    if signals["injection"]:
        category = "unknown"
        category_score = 0
        runner_up_score = 0
    priority = _priority_for(normalized, category, words, signals)
    confidence = _confidence(raw, category_score, runner_up_score, words, signals)
    needs_human = _needs_human(priority, confidence, category, signals)

    if not raw.strip():
        category = "unknown"
        priority = "P3"
        confidence = 0.05
        needs_human = True

    return {
        "id": message_id,
        "category": category,
        "priority": priority,
        "summary": _summary(raw),
        "suggested_action": ACTION_BY_CATEGORY[category],
        "needs_human": needs_human,
        "confidence": round(max(0.0, min(1.0, confidence)), 2),
    }


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.casefold()).strip()


def _word_count(text: str) -> int:
    return len(re.findall(r"\w+", text))


def _contains_any(text: str, terms: Iterable[str]) -> bool:
    return any(term in text for term in terms)


def _collect_signals(text: str) -> dict[str, bool | int]:
    matched_categories = sum(1 for rule in CATEGORY_RULES if _score_rule(text, rule) > 0)
    return {
        "injection": _contains_any(text, INJECTION_TERMS),
        "angry_or_legal": _contains_any(text, ANGER_TERMS),
        "non_english": _contains_any(text, NON_ENGLISH_HINTS) or _non_ascii_ratio(text) > 0.18,
        "multi_issue": matched_categories >= 2,
        "vague": _word_count(text) <= 4 or (_contains_any(text, VAGUE_TERMS) and _word_count(text) <= 8),
    }


def _classify(text: str) -> tuple[str, int, int]:
    scores = [(_score_rule(text, rule), index, rule.category) for index, rule in enumerate(CATEGORY_RULES)]
    scores.sort(key=lambda item: (-item[0], item[1]))
    top_score, _, category = scores[0]
    runner_up_score = scores[1][0] if len(scores) > 1 else 0
    if top_score <= 0:
        return "unknown", 0, 0
    return category, top_score, runner_up_score


def _score_rule(text: str, rule: CategoryRule) -> int:
    score = 0
    for keyword in rule.keywords:
        if keyword in text:
            score += 2 if " " in keyword else 1
    return score


def _priority_for(text: str, category: str, words: int, signals: dict[str, bool | int]) -> str:
    if category == "security" and any(term in text for term in ("breach", "fraud", "hacked", "stolen")):
        return "P0"
    if any(term in text for term in ("down for everyone", "all users", "cannot process orders", "data leak")):
        return "P0"
    if category in ("security", "billing") and signals["angry_or_legal"]:
        return "P1"
    if category in ("account_access", "technical_issue") and any(term in text for term in ("cannot", "can't", "blocked", "urgent", "asap", "no puedo")):
        return "P1"
    if category in ("billing", "shipping", "technical_issue", "account_access", "cancellation", "complaint"):
        return "P2"
    if words <= 4 or category in ("sales_question", "out_of_scope", "unknown"):
        return "P3"
    return "P2"


def _confidence(
    raw: str,
    top_score: int,
    runner_up_score: int,
    words: int,
    signals: dict[str, bool | int],
) -> float:
    if not raw.strip():
        return 0.05

    confidence = 0.35 + min(top_score, 6) * 0.09
    if top_score == 0:
        confidence = 0.2
    if runner_up_score and top_score - runner_up_score <= 1:
        confidence -= 0.18
    if signals["multi_issue"]:
        confidence -= 0.12
    if signals["injection"]:
        confidence -= 0.25
    if signals["non_english"]:
        confidence -= 0.18
    if signals["vague"]:
        confidence -= 0.22
    if words > 120:
        confidence -= 0.12
    if 7 <= words <= 60 and top_score > 0 and not signals["injection"]:
        confidence += 0.08
    return confidence


def _needs_human(priority: str, confidence: float, category: str, signals: dict[str, bool | int]) -> bool:
    return bool(
        priority in ("P0", "P1")
        or (confidence < 0.62 and category != "out_of_scope")
        or category in ("security", "complaint", "unknown")
        or signals["multi_issue"]
        or signals["injection"]
        or signals["angry_or_legal"]
        or signals["non_english"]
    )


def _summary(raw: str) -> str:
    text = re.sub(r"\s+", " ", raw).strip()
    if not text:
        return "No usable customer message was provided."
    text = _redact_lightly(text)
    if len(text) <= 150:
        return text
    clipped = text[:147].rsplit(" ", 1)[0].rstrip(".,;: ")
    return f"{clipped}..."


def _redact_lightly(text: str) -> str:
    text = re.sub(r"[\w.+-]+@[\w-]+\.[\w.-]+", "[email]", text)
    text = re.sub(r"\b(?:\d[ -]*?){13,16}\b", "[card]", text)
    return text


def _non_ascii_ratio(text: str) -> float:
    if not text:
        return 0.0
    return sum(1 for char in text if ord(char) > 127) / len(text)






