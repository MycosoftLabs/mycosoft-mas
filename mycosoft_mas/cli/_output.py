"""Output formatting for the myca CLI.

Supports three output modes:
- json (default): Machine-readable JSON, ideal for agents and piping
- table: Human-friendly aligned columns
- plain: Key=value pairs for simple scripting
"""

from __future__ import annotations

import json
import sys
from typing import Any, Dict, List, Optional, Sequence, Union


def print_result(
    data: Any,
    fmt: str = "json",
    *,
    keys: Optional[Sequence[str]] = None,
    headers: Optional[Sequence[str]] = None,
) -> None:
    """Print data in the requested format.

    Args:
        data: dict, list of dicts, or any JSON-serializable value.
        fmt: "json", "table", or "plain".
        keys: For table/plain, which dict keys to include (in order).
        headers: Column headers for table mode (defaults to keys).
    """
    if fmt == "json":
        _print_json(data)
    elif fmt == "table":
        _print_table(data, keys=keys, headers=headers)
    elif fmt == "plain":
        _print_plain(data, keys=keys)
    else:
        _print_json(data)


def print_error(message: str, *, hint: str = "", exit_code: int = 1) -> None:
    """Print an actionable error and exit.

    Agents self-correct from structured error messages.
    Always includes a hint showing the correct invocation.
    """
    print(f"Error: {message}", file=sys.stderr)
    if hint:
        print(f"  {hint}", file=sys.stderr)
    sys.exit(exit_code)


def print_success(message: str, data: Optional[Dict[str, Any]] = None, fmt: str = "json") -> None:
    """Print a success message. In JSON mode, wraps in a result object."""
    if fmt == "json":
        result: Dict[str, Any] = {"status": "ok", "message": message}
        if data:
            result.update(data)
        _print_json(result)
    else:
        print(message)
        if data:
            for k, v in data.items():
                print(f"  {k}: {v}")


def _print_json(data: Any) -> None:
    """Print JSON to stdout."""
    print(json.dumps(data, indent=2, default=str))


def _print_table(
    data: Any,
    *,
    keys: Optional[Sequence[str]] = None,
    headers: Optional[Sequence[str]] = None,
) -> None:
    """Print data as aligned table."""
    rows = _to_rows(data)
    if not rows:
        print("(no results)")
        return

    if keys is None:
        keys = list(rows[0].keys())
    if headers is None:
        headers = [k.upper().replace("_", " ") for k in keys]

    # Calculate column widths
    widths = [len(h) for h in headers]
    str_rows: List[List[str]] = []
    for row in rows:
        str_row = [str(row.get(k, "")) for k in keys]
        for i, cell in enumerate(str_row):
            if i < len(widths):
                widths[i] = max(widths[i], len(cell))
        str_rows.append(str_row)

    # Print header
    header_line = "  ".join(h.ljust(widths[i]) for i, h in enumerate(headers))
    print(header_line)
    print("  ".join("-" * w for w in widths))

    # Print rows
    for str_row in str_rows:
        line = "  ".join(
            str_row[i].ljust(widths[i]) if i < len(widths) else str_row[i]
            for i in range(len(str_row))
        )
        print(line)


def _print_plain(data: Any, *, keys: Optional[Sequence[str]] = None) -> None:
    """Print key=value pairs, one per line."""
    rows = _to_rows(data)
    if not rows:
        return

    if keys is None:
        keys = list(rows[0].keys())

    for row in rows:
        parts = [f"{k}={row.get(k, '')}" for k in keys]
        print(" ".join(parts))


def _to_rows(data: Any) -> List[Dict[str, Any]]:
    """Normalize data to a list of dicts for table/plain output."""
    if isinstance(data, list):
        return [r if isinstance(r, dict) else {"value": r} for r in data]
    if isinstance(data, dict):
        # If the dict contains a list value that looks like results, use that
        for key in ("agents", "tasks", "results", "items", "services", "memories", "workflows"):
            if key in data and isinstance(data[key], list):
                return [r if isinstance(r, dict) else {"value": r} for r in data[key]]
        return [data]
    return [{"value": data}]
