# FRONTLINE — Offline-First Customer Message Triage

> Turns raw, messy customer messages into structured, actionable triage decisions — instantly, with zero API cost by default.

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)
![License](https://img.shields.io/badge/license-MIT-green)
![Cost](https://img.shields.io/badge/offline%20cost-%240.00-brightgreen)
![Groq](https://img.shields.io/badge/Groq-optional-orange?logo=groq)

---

## What It Does

Every message in `data/messages.jsonl` is processed into a structured JSON decision:

```json
{
  "category": "billing",
  "priority": "P2",
  "summary": "Charged twice for April subscription, requesting refund.",
  "suggested_action": "Review billing records and issue a partial refund.",
  "needs_human": false,
  "confidence": 0.78
}
```

**Key capabilities:**

| Feature | Detail |
|---------|--------|
| 🔌 Zero-dependency offline engine | Runs on Python stdlib only — no API key required |
| 🤖 Optional Groq LLM backend | Upgrade uncertain cases with `llama-3.1-8b-instant` |
| 🔀 Hybrid routing | Offline handles confident cases; Groq handles edge cases |
| 🛡️ Prompt-injection resistance | Customer messages never influence their own classification |
| 🌐 Multilingual detection | Non-English messages auto-escalate to human review |
| 💰 Real cost reporting | Token-accurate USD estimates for Groq and hybrid modes |
| 📊 Evaluation suite | Measures category, priority, and human-flag agreement |
| ⚡ Fast | ~0.2 ms/message offline; ~2.5 s/message with Groq throttle |

---

## Quick Start

### Option 1 — No install (set PYTHONPATH)

```powershell
$env:PYTHONPATH = "src"
python -m frontline run --table
```

### Option 2 — Editable install (recommended)

```powershell
python -m pip install -e .
python -m frontline run --table
```

---

## Modes

### Offline (default) — `$0.00`

Pure rules engine. Processes all 40 messages in under 10 ms.

```powershell
python -m frontline run --mode offline --table
```

```
Processed 40 messages in 8.3 ms (0.21 ms/message).
Saved predictions to out\triage.json. Offline model cost: $0.00.
```

---

### Groq — LLM-powered

Sends every message to Groq's `llama-3.1-8b-instant` model.
Requires `GROQ_API_KEY` in your `.env` or environment.

```powershell
python -m frontline run --mode groq --table
```

```
Processed 40 messages in 99,098.6 ms (2,477 ms/message).
Saved predictions to out\triage.json. Groq cost: ~$0.000481
  (5,471 prompt + 2,590 completion tokens, model: llama-3.1-8b-instant).
```

> **Rate limit:** The free Groq tier allows 30 requests/min.
> FRONTLINE automatically throttles to 2 s between calls to stay within that limit.

---

### Hybrid — Best of both worlds

The offline engine runs first. If confidence is low, the category is unknown,
or the message needs human review, it escalates to Groq.

```powershell
python -m frontline run --mode hybrid --table
```

```
Processed 40 messages in 91,354.0 ms (2,283 ms/message).
Saved predictions to out\triage.json. Offline model cost: $0.00.
  Groq cost: ~$0.000432 (4,915 prompt + 2,328 completion tokens, model: llama-3.1-8b-instant).
```

> Hybrid uses **fewer tokens than full Groq mode** because confident messages never reach the API.

---

## All CLI Options

```
python -m frontline run  [--input PATH] [--output PATH]
                         [--mode offline|hybrid|groq]
                         [--model GROQ_MODEL_NAME]
                         [--table] [--json]

python -m frontline eval [--truth PATH] [--predictions PATH]
```

| Flag | Default | Description |
|------|---------|-------------|
| `--input` | `data/messages.jsonl` | Input messages |
| `--output` | `out/triage.json` | Output predictions |
| `--mode` | `offline` | Triage engine to use |
| `--model` | `llama-3.1-8b-instant` | Groq model name |
| `--table` | off | Print a CLI table |
| `--json` | off | Print JSON to stdout |

---

## Environment Variables

Copy `.env.example` to `.env` and fill in your key:

```ini
GROQ_API_KEY=gsk_...          # Required for groq / hybrid modes
GROQ_MODEL=llama-3.1-8b-instant  # Optional: override model
GROQ_TIMEOUT_SECONDS=20          # Optional: request timeout
```

---

## Evaluation

```powershell
python -m frontline eval
```

```
Evaluated 10 hand-labeled messages
Category agreement:     100.0%
Priority agreement:     100.0%
Human-flag agreement:   100.0%
Exact triage agreement: 100.0%

No failures against the current hand labels.
```

---

## Running Tests

```powershell
python -m unittest
```

Tests cover: JSON field validity · priority constraints · prompt-injection resistance ·
vague input escalation · multilingual detection · evaluation math.

---

## Project Structure

```
FrontLine/
├── src/frontline/
│   ├── triage.py         # Offline rules engine (keyword scoring, risk flags)
│   ├── groq_client.py    # Groq API client (token tracking, cost estimation)
│   ├── hybrid.py         # Hybrid routing logic
│   ├── cli.py            # CLI entry point (all modes + cost summary)
│   ├── eval.py           # Evaluation against ground truth
│   ├── io.py             # JSONL / JSON I/O helpers
│   └── env.py            # .env loader
├── data/
│   ├── messages.jsonl    # 40 challenge messages
│   └── ground_truth.jsonl # 10 hand-labeled examples
├── out/
│   └── triage.json       # Generated predictions
├── tests/                # Unit tests
├── .env.example          # Environment variable template
├── AI_DECISIONS.md       # Design rationale and decision log
└── pyproject.toml        # Package metadata
```

---

## Groq Model Pricing Reference

Costs are calculated automatically based on the model used:

| Model | Input ($/1M tok) | Output ($/1M tok) |
|-------|-----------------|-------------------|
| `llama-3.1-8b-instant` | $0.05 | $0.08 |
| `llama3-8b-8192` | $0.05 | $0.08 |
| `gemma2-9b-it` | $0.20 | $0.20 |
| `mixtral-8x7b-32768` | $0.24 | $0.24 |
| `llama-3.3-70b-versatile` | $0.59 | $0.79 |
| `llama3-70b-8192` | $0.59 | $0.79 |

---

*Built for the FRONTLINE AI build challenge · Python 3.10+ · Zero required dependencies*
