# FRONTLINE — Offline-First Customer Message Triage

> Turns raw, messy customer messages into structured, actionable triage decisions — instantly, with zero API cost by default.

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)
![Offline Cost](https://img.shields.io/badge/offline%20cost-%240.00-brightgreen)
![Eval](https://img.shields.io/badge/eval-100%25%20all%20modes-success)
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
| 🤖 Optional Groq LLM backend | Semantic classification with `llama-3.1-8b-instant` |
| 🔀 Hybrid routing | Offline handles confident cases; Groq handles uncertain ones |
| 🛡️ Injection resistance (all modes) | `confidence=0.0` messages never reach the LLM |
| 🔁 Auto-retry on 429 | Reads Groq's rate-limit header, waits exact time, retries once |
| 🌐 Multilingual escalation | Non-English messages always flagged for human review |
| 💰 Real cost reporting | Token-accurate USD estimates per run per mode |
| 📊 100% eval accuracy | All three modes score 100% on 10 hand-labelled ground-truth cases |
| ⚡ Fast | ~0.2 ms/message offline · ~2.5 s/message with Groq (throttled) |

---

## Quick Start

### Option 1 — Editable install (recommended)
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

Every message classified by `llama-3.1-8b-instant`. Injection/empty messages are
pre-screened by the offline engine and **never sent to the LLM**.

Requires `GROQ_API_KEY` in `.env`.

```powershell
python -m frontline run --mode groq --output out/triage_groq.json --table
```
```
Processed 40 messages in 99,098 ms (2,477 ms/message).
Saved predictions to out\triage_groq.json.
Groq cost: ~$0.000570 (7,151 prompt + 2,660 completion tokens, model: llama-3.1-8b-instant).
```

> **Rate limit:** Free tier = 30 RPM. FRONTLINE throttles to 2 s between calls.
> If the bucket is already full, it reads the `x-ratelimit-reset-requests` header and
> waits exactly that long before auto-retrying — no manual intervention needed:
> ```
> [frontline] Groq rate limit hit — waiting 47s for window reset...
> ```

> **Total fallback:** If Groq is completely unavailable, the run finishes offline:
> ```
> Offline model cost: $0.00. Groq unavailable (...) — all messages processed offline.
> ```

---

### 🔀 Hybrid — Best of both worlds

Offline engine runs first. Groq is only called when confidence < 0.70, category is
`unknown`, or `needs_human` is true. Injection/empty messages are pre-screened and
never sent to Groq.

```powershell
python -m frontline run --mode hybrid --output out/triage_hybrid.json --table
```
```
Processed 40 messages in 91,354 ms (2,283 ms/message).
Saved predictions to out\triage_hybrid.json. Offline model cost: $0.00.
Groq cost: ~$0.000432 (4,915 prompt + 2,328 completion tokens, model: llama-3.1-8b-instant).
```

> Hybrid uses **fewer tokens than full Groq** because confident messages stay offline.

---

## Evaluation — All Modes Score 100%

```powershell
# Offline
python -m frontline run --mode offline
python -m frontline eval

# Groq
python -m frontline run --mode groq --output out/triage_groq.json
python -m frontline eval --predictions out/triage_groq.json

# Hybrid
python -m frontline run --mode hybrid --output out/triage_hybrid.json
python -m frontline eval --predictions out/triage_hybrid.json
```

| Mode | Category | Priority | Human-flag | Exact |
|------|----------|----------|------------|-------|
| Offline | 100% | 100% | 100% | 100% |
| Groq | 100% | 100% | 100% | 100% |
| Hybrid | 100% | 100% | 100% | 100% |

---

## All Run Commands

```powershell
# OFFLINE
python -m frontline run --mode offline --table
python -m frontline run --mode offline --input data/messages.jsonl --output out/triage_offline.json --table

# GROQ
python -m frontline run --mode groq --table
python -m frontline run --mode groq --input data/messages.jsonl --output out/triage_groq.json --table

# HYBRID
python -m frontline run --mode hybrid --table
python -m frontline run --mode hybrid --input data/messages.jsonl --output out/triage_hybrid.json --table

# EVAL
python -m frontline eval
python -m frontline eval --predictions out/triage_groq.json
python -m frontline eval --predictions out/triage_hybrid.json

# MOCK 200 STRESS TEST
python -m frontline run --mode offline --input data/mock_200.jsonl --output out/mock_triage.json --table

# UNIT TESTS
python -m unittest
```

---

## Environment Variables

Copy `.env.example` to `.env`:

```ini
GROQ_API_KEY=gsk_...              # Required for groq / hybrid modes
GROQ_MODEL=llama-3.1-8b-instant  # Optional: override model
GROQ_TIMEOUT_SECONDS=20          # Optional: request timeout
```

---

## Running Tests

```powershell
python -m unittest
```
```
Ran 18 tests in 0.083s
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
| `out/triage.json` | Predictions from the last `run` command |

**Input format:**
```jsonl
{"id": "msg-001", "message": "I was charged twice for my April subscription."}
```

**Output format:**
```json
[
  {
    "category": "billing",
    "priority": "P2",
    "summary": "Charged twice for April subscription.",
    "suggested_action": "Review billing records and issue a refund.",
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
│   ├── groq_client.py    # Groq API client (prompt, retry, token cost)
│   ├── hybrid.py         # Hybrid routing with injection pre-screen
│   ├── cli.py            # CLI — all modes, injection guard, cost summary
│   ├── eval.py           # Evaluation against ground truth
│   ├── io.py             # JSONL / JSON I/O helpers
│   └── env.py            # .env loader
├── data/
│   ├── messages.jsonl        # 40 challenge messages
│   ├── ground_truth.jsonl    # 10 hand-labelled examples
│   └── mock_200.jsonl        # 200 synthetic stress-test messages
├── out/
│   └── triage.json           # Generated predictions
├── tests/                    # 18 unit tests
├── .env.example              # Environment variable template
├── AI_DECISIONS.md           # Design rationale and decision log
└── pyproject.toml            # Package metadata (Python 3.10+)
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

Cost is calculated automatically per run from actual token usage.

---

*Built for the FRONTLINE AI build challenge · Python 3.10+ · Zero required dependencies*
