"""Normalise, dedupe, sort and write permit rows."""

from __future__ import annotations

import csv
import io
from collections.abc import Iterable
from pathlib import Path
from typing import Any


def _text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, dict):  # Socrata location/url objects
        return str(value.get("human_address") or value.get("url") or "")
    return str(value).strip()


def normalize(
    rows: Iterable[dict[str, Any]],
    fields: list[str] | None = None,
    date_fields: Iterable[str] = (),
) -> list[dict[str, str]]:
    """Flatten rows to strings, keep ``fields`` (or every key seen), trim dates to YYYY-MM-DD."""
    rows = list(rows)
    if fields is None:
        fields = []
        for r in rows:
            fields.extend(k for k in r if k not in fields and not k.startswith(":"))
    dates = set(date_fields)
    out = []
    for r in rows:
        d = {f: _text(r.get(f)) for f in fields}
        for f in dates & d.keys():
            d[f] = d[f][:10]
        out.append(d)
    return out


def dedupe(rows: Iterable[dict[str, str]], key: str) -> list[dict[str, str]]:
    """Keep the first row per non-empty ``key``; rows with an empty key are dropped."""
    seen: set[str] = set()
    out = []
    for r in rows:
        k = r.get(key, "")
        if not k or k in seen:
            continue
        seen.add(k)
        out.append(r)
    return out


def sort_rows(rows: list[dict[str, str]], date_field: str, key: str) -> list[dict[str, str]]:
    """Newest first; ties broken by the higher key (usually the later-filed permit)."""
    return sorted(rows, key=lambda r: (r.get(date_field, ""), r.get(key, "")), reverse=True)


def write_csv(rows: list[dict[str, str]], path: str | Path, fields: list[str] | None = None) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = fields or (list(rows[0]) if rows else [])
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    return path


def _cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")


def to_markdown(rows: list[dict[str, str]], fields: list[str] | None = None, title: str | None = None) -> str:
    fields = fields or (list(rows[0]) if rows else [])
    buf = io.StringIO()
    if title:
        buf.write(f"# {title}\n\n")
    buf.write("| " + " | ".join(fields) + " |\n")
    buf.write("|" + "|".join("---" for _ in fields) + "|\n")
    for r in rows:
        buf.write("| " + " | ".join(_cell(r.get(f, "")) for f in fields) + " |\n")
    return buf.getvalue()
