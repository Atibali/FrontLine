"""Command line interface for FRONTLINE triage."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

from .env import load_dotenv
from .eval import evaluate
from .groq_client import GroqClient, GroqClientError
from .hybrid import triage_hybrid
from .io import read_json, read_jsonl, write_json
from .triage import triage_message

DEFAULT_INPUT = Path("data/messages.jsonl")
DEFAULT_OUTPUT = Path("out/triage.json")
_GROQ_THROTTLE_SECS = float(os.environ.get("GROQ_THROTTLE_SECS", "0"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="frontline",
        description="Offline-first customer message triage.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="triage a JSONL message dataset")
    run_parser.add_argument("--input", default=str(DEFAULT_INPUT), help="JSONL input path")
    run_parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="JSON output path")
    run_parser.add_argument("--table", action="store_true", help="print a CLI table")
    run_parser.add_argument("--json", action="store_true", help="print JSON to stdout")
    run_parser.add_argument(
        "--mode",
        choices=("offline", "hybrid", "groq"),
        default="offline",
        help="choose offline rules, hybrid routing, or Groq-only mode",
    )
    run_parser.add_argument(
        "--model",
        default=os.environ.get("GROQ_MODEL", "llama-3.1-8b-instant"),
        help="Groq model name",
    )

    eval_parser = subparsers.add_parser("eval", help="compare predictions to ground truth")
    eval_parser.add_argument("--input", default=str(DEFAULT_INPUT), help="original JSONL input path")
    eval_parser.add_argument("--truth", default="data/ground_truth.jsonl", help="ground truth JSONL path")
    eval_parser.add_argument("--predictions", default=str(DEFAULT_OUTPUT), help="prediction JSON path")

    args = parser.parse_args(argv)
    if args.command == "run":
        return _run(args)
    if args.command == "eval":
        return _eval(args)
    parser.error("unknown command")
    return 2


def _run(args: argparse.Namespace) -> int:
    load_dotenv()
    start = time.perf_counter()
    rows = read_jsonl(args.input)
    predictions = []
    table_rows = []
    groq_client = None
    groq_disabled_reason = None

    if args.mode in ("hybrid", "groq"):
        try:
            groq_client = GroqClient()
        except GroqClientError as exc:
            if args.mode == "groq":
                groq_disabled_reason = str(exc)
                groq_client = None
            else:
                groq_client = None

    for index, row in enumerate(rows, start=1):
        item_id = str(row.get("id") or f"msg-{index:03d}")
        message = row.get("message", "")
        if args.mode == "offline" or groq_client is None:
            decision = triage_message(message, item_id)
        elif args.mode == "groq":
            try:
                decision = groq_client.triage("" if message is None else str(message))
                if _GROQ_THROTTLE_SECS:
                    time.sleep(_GROQ_THROTTLE_SECS)
            except GroqClientError as exc:
                if groq_disabled_reason is None:
                    groq_disabled_reason = str(exc)
                groq_client = None
                decision = triage_message(message, item_id)
        else:
            decision = triage_hybrid(message, item_id, groq_client=groq_client)
            if _GROQ_THROTTLE_SECS:
                time.sleep(_GROQ_THROTTLE_SECS)
        predictions.append(decision)
        table_row = {"id": item_id, **decision}
        if row.get("_input_error"):
            table_row["input_error"] = row["_input_error"]
            table_row["needs_human"] = True
            table_row["confidence"] = min(table_row["confidence"], 0.2)
        table_rows.append(table_row)

    elapsed_ms = (time.perf_counter() - start) * 1000
    write_json(args.output, predictions)

    if groq_disabled_reason is not None and args.mode == "groq":
        print(f"Groq mode failed, falling back to offline triage: {groq_disabled_reason}", file=sys.stderr)

    if args.table:
        print(_table(table_rows))
    if args.json:
        print(json.dumps(predictions, indent=2, ensure_ascii=False))

    per_message = elapsed_ms / max(1, len(predictions))
    print(f"\nProcessed {len(predictions)} messages in {elapsed_ms:.1f} ms ({per_message:.2f} ms/message).")
    print(f"Saved predictions to {args.output}. {_cost_summary(args.mode, groq_client, groq_disabled_reason)}")
    return 0


def _cost_summary(mode: str, groq_client, groq_disabled_reason: str | None = None) -> str:
    """Return a human-readable cost string appropriate for the triage mode."""
    offline_part = "Offline model cost: $0.00."
    if mode == "offline" or groq_client is None:
        return offline_part
    prompt_tok, completion_tok = groq_client.token_usage()
    # Groq was configured but every call fell back (rate limited, network error, etc.)
    if prompt_tok == 0 and completion_tok == 0:
        reason = f" ({groq_disabled_reason})" if groq_disabled_reason else ""
        return f"{offline_part} Groq unavailable{reason} — all messages processed offline."
    cost = groq_client.estimated_cost()
    groq_part = (
        f"Groq cost: ~${cost:.6f} "
        f"({prompt_tok:,} prompt + {completion_tok:,} completion tokens, "
        f"model: {groq_client.config.model})."
    )
    if mode == "hybrid":
        return f"{offline_part} {groq_part}"
    return groq_part  # groq-only mode


def _eval(args: argparse.Namespace) -> int:
    truth = read_jsonl(args.truth)
    source_rows = read_jsonl(args.input)
    predictions = read_json(args.predictions)
    result = evaluate(truth, predictions, source_rows=source_rows)
    print(f"Evaluated {result.total} hand-labeled messages")
    print(f"Category agreement:    {_pct(result.category_accuracy)}")
    print(f"Priority agreement:    {_pct(result.priority_accuracy)}")
    print(f"Human-flag agreement:  {_pct(result.human_accuracy)}")
    print(f"Exact triage agreement:{_pct(result.exact_accuracy)}")

    if result.failures:
        print("\nFailure examples:")
        for failure in result.failures[:5]:
            print(f"- {failure}")
    else:
        print("\nNo failures against the current hand labels.")
    return 0


def _pct(value: float) -> str:
    return f"{value * 100:5.1f}%"


def _table(rows: list[dict]) -> str:
    headers = ("ID", "Category", "Pri", "Conf", "Human", "Summary")
    widths = (8, 16, 3, 5, 5, 70)
    lines = [_format_row(headers, widths), _format_row(tuple("-" * width for width in widths), widths)]
    for row in rows:
        lines.append(
            _format_row(
                (
                    str(row.get("id", "")),
                    str(row.get("category", "")),
                    str(row.get("priority", "")),
                    f"{float(row.get('confidence', 0)):.2f}",
                    "yes" if row.get("needs_human") else "no",
                    str(row.get("summary", "")),
                ),
                widths,
            )
        )
    return "\n".join(lines)


def _format_row(values: tuple[str, ...], widths: tuple[int, ...]) -> str:
    return " | ".join(_clip(value, width).ljust(width) for value, width in zip(values, widths))


def _clip(value: str, width: int) -> str:
    value = value.encode("ascii", errors="replace").decode("ascii")
    if len(value) <= width:
        return value
    return value[: max(0, width - 3)] + "..."
