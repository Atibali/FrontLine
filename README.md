# FRONTLINE - Offline Customer Message Triage

FRONTLINE turns messy customer messages into structured triage decisions:

```json
{
  "category": "billing",
  "priority": "P2",
  "summary": "I was charged twice for my April subscription...",
  "suggested_action": "Review billing records...",
  "needs_human": false,
  "confidence": 0.78
}
```

It is built for the one-day AI challenge: offline by default, with an optional Groq-backed hybrid mode if you set `GROQ_API_KEY`.

## Quick Start

From this folder:

```powershell
$env:PYTHONPATH="src"
python -m frontline run --input data/messages.jsonl --output out/triage.json --table
python -m frontline eval --truth data/ground_truth.jsonl --predictions out/triage.json
python -m unittest
```

Hybrid mode with Groq:

```powershell
$env:PYTHONPATH="src"
$env:GROQ_API_KEY="your_key_here"
python -m frontline run --mode hybrid --table
```

Optional editable install, if you prefer not to set `PYTHONPATH`:

```powershell
python -m pip install -e .
python -m frontline run --table
```

## What It Does

- Processes every message in `data/messages.jsonl`.
- Emits strict JSON predictions to `out/triage.json`.
- Shows a CLI table for the live demo.
- Flags uncertain, ambiguous, adversarial, security-sensitive, legal, non-English, and P0/P1 messages for human review.
- Can optionally call Groq for low-confidence cases while keeping the offline guardrails as fallback.
- Measures agreement against 10 hand-labeled examples in `data/ground_truth.jsonl`.
- Reports latency per message and offline cost.

## Demo Script

1. Run the CLI table:

   ```powershell
   $env:PYTHONPATH="src"
   python -m frontline run --table
   ```

2. Point out clear cases, risky cases, and the prompt-injection row.
3. Show the saved JSON:

   ```powershell
   Get-Content out/triage.json -TotalCount 40
   ```

4. Run evaluation:

   ```powershell
   python -m frontline eval
   ```

5. Explain `AI_DECISIONS.md`: transparent rules, conservative escalation, measured accuracy, zero API cost, and hybrid routing for uncertain cases.

## Judging Checklist

- **Works end-to-end:** `run` handles all 40 messages and writes JSON.
- **Reliable:** low-confidence and unsafe cases route to humans.
- **AI understanding:** the rules mimic a guarded classifier and are easy to replace with an LLM later.
- **Evaluation:** 10 hand labels measure category, priority, human flag, and exact agreement.
- **Craft:** CLI table, clean package, tests, and one-page decision note.
