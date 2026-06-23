# AI Decisions Note

## Model and Tools

This project uses an offline hybrid triage engine written in Python standard library only. Instead of depending on an API key during the demo, it uses transparent category signals, risk rules, confidence scoring, and conservative human escalation. The output shape is LLM-ready, so a hosted model can later replace or assist the classifier without changing the CLI contract.

## Strategy

The system treats each customer message as untrusted input. It never executes instructions inside the message and it never lets a message choose its own category, priority, or JSON fields. The classifier scores category keyword groups, then lowers confidence for ambiguity, multi-issue messages, prompt-injection language, vague text, very long input, and likely non-English messages.

## Uncertainty and Bad Input

`needs_human` becomes true for low confidence, P0/P1 severity, security risk, legal or angry language, prompt injection, ambiguous multi-issue input, unknown category, and non-English messages. Empty or malformed input still produces valid JSON with `unknown`, low confidence, and human review.

## How We Know It Works

The repo includes 40 challenge-style messages and 10 hand-labeled ground truth examples. Current evaluation reports 100% category agreement, 100% priority agreement, 100% human-flag agreement, and 100% exact triage agreement on those labels. Unit tests verify valid JSON fields, priority constraints, injection resistance, vague input escalation, multilingual handling, and evaluation math.

## Cost, Latency, and Next Step

Offline demo cost is `$0.00`. A local run processed 40 messages in about 13 ms, roughly 0.32 ms per message. With more time, the best improvement would be an optional LLM verifier that only runs on low-confidence or high-risk messages, cutting cost while improving summaries and edge-case classification.

