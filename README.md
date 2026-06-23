# FRONTLINE — Offline-First Customer Message Triage

> Turns raw, messy customer messages into structured, actionable triage decisions — instantly, with zero API cost by default.

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)
![License](https://img.shields.io/badge/license-MIT-green)
![Offline Cost](https://img.shields.io/badge/offline%20cost-%240.00-brightgreen)
![Groq](https://img.shields.io/badge/Groq-optional-orange)

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
  "confidence": 0.79
}
```

**Key capabilities:**

| Feature | Detail |
|---------|--------|
| 🔌 Zero-dependency offline engine | Runs on Python stdlib only — no API key required |
| 🤖 Optional Groq LLM backend | Upgrade uncertain cases with `llama-3.1-8b-instant` |
| 🔀 Hybrid routing | Offline handles confident cases; Groq handles edge cases |
| 🔁 Auto-retry on 429 | Reads Groq's rate-limit header and waits the exact right time |
| 🛡️ Prompt-injection resistance | Customer messages never influence their own classification |
| 🌐 Multilingual detection | Non-English messages auto-escalate to human review |
| 💰 Real cost reporting | Token-accurate USD estimates per run |
| 📊 Evaluation suite | Measures category, priority, and human-flag agreement |
| ⚡ Fast | ~0.2 ms/message offline · ~2.5 s/message with Groq (throttled) |

---

## Quick Start

### Option 1 — Editable install (recommended, no PYTHONPATH needed)

```powershell
python -m pip install -e .
python -m frontline run --table
```

### Option 2 — No install

```powershell
$env:PYTHONPATH = "src"
python -m frontline run --table
```

---

## Modes

### 🔌 Offline — `$0.00`, instant

Pure keyword rules engine. Processes all 40 messages in under 10 ms. No API key needed.

```powershell
python -m frontline run --mode offline --table
```

```
Processed 40 messages in 7.8 ms (0.20 ms/message).
Saved predictions to out\triage.json. Offline model cost: $0.00.
```

---

### 🤖 Groq — LLM-powered

Sends every message to Groq's `llama-3.1-8b-instant`. Requires `GROQ_API_KEY` in `.env`.

```powershell
python -m frontline run --mode groq --table
```

```
Processed 40 messages in 99,098 ms (2,477 ms/message).
Saved predictions to out\triage.json. Groq cost: ~$0.000481
  (5,471 prompt + 2,590 completion tokens, model: llama-3.1-8b-instant).
```

> **Rate limit:** Free tier = 30 RPM. FRONTLINE throttles to 2 s between calls.
> If the bucket is already full it reads Groq's `x-ratelimit-reset-requests` header
> and waits exactly that long before auto-retrying — no manual intervention needed.

If Groq is completely unavailable the run finishes offline and tells you clearly:

```
Offline model cost: $0.00. Groq unavailable (429 Too Many Requests) — all messages processed offline.
```

---

### 🔀 Hybrid — Best of both worlds

Offline engine runs first. Only uncertain messages (low confidence, unknown category, or
flagged for human review) are escalated to Groq — saving tokens and keeping costs low.

```powershell
python -m frontline run --mode hybrid --table
```

```
Processed 40 messages in 91,354 ms (2,283 ms/message).
Saved predictions to out\triage.json. Offline model cost: $0.00.
  Groq cost: ~$0.000432 (4,915 prompt + 2,328 completion tokens, model: llama-3.1-8b-instant).
```

> Hybrid uses **fewer tokens than full Groq** because confident messages never hit the API.

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
| `--input` | `data/messages.jsonl` | Input messages (JSONL) |
| `--output` | `out/triage.json` | Output predictions (JSON) |
| `--mode` | `offline` | Triage engine to use |
| `--model` | `llama-3.1-8b-instant` | Groq model name |
| `--table` | off | Print a formatted CLI table |
| `--json` | off | Print raw JSON to stdout |

---

## Common Run Commands

```powershell
# --- OFFLINE ---
python -m frontline run --mode offline --table
python -m frontline run --mode offline --input data/messages.jsonl --output out/triage_offline.json --table

# --- GROQ ---
python -m frontline run --mode groq --table
python -m frontline run --mode groq --input data/messages.jsonl --output out/triage_groq.json --table

# --- HYBRID ---
python -m frontline run --mode hybrid --table
python -m frontline run --mode hybrid --input data/messages.jsonl --output out/triage_hybrid.json --table

# --- EVAL (always reads out/triage.json unless told otherwise) ---
python -m frontline eval
python -m frontline eval --predictions out/triage_groq.json

# --- MOCK 200 STRESS TEST ---
python -m frontline run --mode offline --input data/mock_200.jsonl --output out/mock_triage.json --table

# --- UNIT TESTS ---
python -m unittest
```

---

## Environment Variables

Copy `.env.example` to `.env` and fill in your key:

```ini
GROQ_API_KEY=gsk_...              # Required for groq / hybrid modes
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

> Run `python -m frontline run --mode offline` first to regenerate `out/triage.json`
> before evaluating, since Groq runs overwrite the same file.

---

## Running Tests

```powershell
python -m unittest
```

```
Ran 18 tests in 0.061s
OK
```

Tests cover: JSON schema validity · priority constraints · confidence bounds ·
prompt-injection resistance · vague input escalation · multilingual detection ·
hybrid routing · evaluation math.

---

## Data & Output Files

| File | Role |
|------|------|
| `data/messages.jsonl` | 40 raw customer messages (input) |
| `data/ground_truth.jsonl` | 10 hand-labelled correct answers (for eval) |
| `data/mock_200.jsonl` | 200 synthetic messages (stress / scale test) |
| `out/triage.json` | Predictions written by the last `run` command |

**Input format** (`messages.jsonl`):
```jsonl
{"id": "msg-001", "message": "I was charged twice for my April subscription."}
```

**Output format** (`triage.json`):
```json
[
  {
    "category": "billing",
    "priority": "P2",
    "summary": "...",
    "suggested_action": "...",
    "needs_human": false,
    "confidence": 0.79
  }
]
```

---

## Project Structure

```
FrontLine/
├── src/frontline/
│   ├── triage.py         # Offline keyword rules engine
│   ├── groq_client.py    # Groq API client (token tracking, retry, cost)
│   ├── hybrid.py         # Hybrid routing logic
│   ├── cli.py            # CLI entry point — all modes + cost summary
│   ├── eval.py           # Evaluation against ground truth
│   ├── io.py             # JSONL / JSON I/O helpers
│   └── env.py            # .env loader
├── data/
│   ├── messages.jsonl    # 40 challenge messages
│   ├── ground_truth.jsonl # 10 hand-labelled examples
│   └── mock_200.jsonl    # 200 synthetic stress-test messages
├── out/
│   └── triage.json       # Generated predictions (overwritten each run)
├── tests/                # 18 unit tests
├── .env.example          # Environment variable template
├── AI_DECISIONS.md       # Design rationale and decision log
└── pyproject.toml        # Package metadata (Python 3.10+)
```

---

## Groq Model Pricing Reference

| Model | Input ($/1M tokens) | Output ($/1M tokens) |
|-------|--------------------|--------------------|
| `llama-3.1-8b-instant` | $0.05 | $0.08 |
| `llama3-8b-8192` | $0.05 | $0.08 |
| `gemma2-9b-it` | $0.20 | $0.20 |
| `mixtral-8x7b-32768` | $0.24 | $0.24 |
| `llama-3.3-70b-versatile` | $0.59 | $0.79 |
| `llama3-70b-8192` | $0.59 | $0.79 |

Cost is calculated automatically per run based on actual token usage.

---

*Built for the FRONTLINE AI build challenge · Python 3.10+ · Zero required dependencies*
