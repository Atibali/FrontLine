"""Input/output helpers for JSONL datasets and triage output."""

from __future__ import annotations

import json
from pathlib import Path


def read_jsonl(path: str | Path) -> list[dict]:
    records: list[dict] = []
    with Path(path).open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                records.append(
                    {
                        "id": f"malformed-{line_no}",
                        "message": line.strip(),
                        "_input_error": f"Invalid JSONL at line {line_no}: {exc.msg}",
                    }
                )
                continue
            if isinstance(value, dict):
                records.append(value)
            else:
                records.append({"id": f"malformed-{line_no}", "message": str(value)})
    return records


def write_json(path: str | Path, records: list[dict]) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(records, indent=2, ensure_ascii=False), encoding="utf-8")


def read_json(path: str | Path) -> list[dict]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, list):
        raise ValueError(f"{path} must contain a JSON array")
    return value
