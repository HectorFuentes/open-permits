"""Command-line entry point: ``open-permits``."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
from collections.abc import Sequence
from pathlib import Path

from . import __version__
from .presets import (
    ORLANDO_DATASET,
    ORLANDO_DATE_FIELD,
    ORLANDO_DOMAIN,
    ORLANDO_FIELDS,
    ORLANDO_KEY,
    ORLANDO_PRESETS,
)
from .query import Window, build_where
from .report import dedupe, normalize, sort_rows, to_markdown, write_csv
from .socrata import SocrataClient


def _date(value: str) -> dt.date:
    try:
        return dt.date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"expected YYYY-MM-DD, got {value!r}") from exc


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="open-permits",
        description="Pull building permits from a Socrata open-data endpoint, filter by type and "
        "date window, dedupe, and write CSV (and optionally Markdown).",
    )
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    src = p.add_argument_group("source")
    src.add_argument("--domain", default=ORLANDO_DOMAIN, help="Socrata domain (default: %(default)s)")
    src.add_argument("--dataset", default=ORLANDO_DATASET, help="dataset id (default: %(default)s)")
    src.add_argument(
        "--app-token",
        default=os.environ.get("SOCRATA_APP_TOKEN"),
        help="optional Socrata app token (default: $SOCRATA_APP_TOKEN)",
    )
    flt = p.add_argument_group("filters")
    flt.add_argument(
        "--preset",
        choices=sorted(ORLANDO_PRESETS),
        help="City of Orlando shortcut for the permit-type filter",
    )
    flt.add_argument("--type-field", default="application_type", help="column holding the permit type")
    flt.add_argument(
        "--type",
        dest="types",
        action="append",
        default=[],
        metavar="VALUE",
        help="permit type to keep; repeat for several (one query per type, results merged)",
    )
    flt.add_argument(
        "--where",
        dest="extra",
        action="append",
        default=[],
        metavar="SOQL",
        help="extra flat SoQL condition, e.g. \"worktype='Roof'\"; repeatable",
    )
    flt.add_argument("--date-field", default=ORLANDO_DATE_FIELD, help="date column (default: %(default)s)")
    flt.add_argument("--since", type=_date, help="first date included (YYYY-MM-DD)")
    flt.add_argument("--until", type=_date, help="last date included (default: yesterday)")
    flt.add_argument("--days", type=int, default=7, help="window length when --since is omitted (default: 7)")
    out = p.add_argument_group("output")
    out.add_argument(
        "--fields",
        help="comma-separated columns to select (default: Orlando preset columns "
        "on the Orlando dataset, otherwise every column)",
    )
    out.add_argument("--key", default=ORLANDO_KEY, help="dedupe key column (default: %(default)s)")
    out.add_argument("--limit", type=int, help="keep only the N newest rows")
    out.add_argument("-o", "--output", default="permits.csv", help="CSV path (default: %(default)s)")
    out.add_argument("--markdown", metavar="PATH", help="also write a Markdown table here")
    out.add_argument(
        "--allow-empty",
        action="store_true",
        help="write a header-only CSV instead of exiting 1 when nothing matches",
    )
    return p


def run(argv: Sequence[str] | None = None, client: SocrataClient | None = None) -> int:
    args = build_parser().parse_args(argv)
    until = args.until or dt.date.today() - dt.timedelta(days=1)
    window = Window(args.since, until) if args.since else Window.last_days(args.days, until)

    if args.fields:
        fields: list[str] | None = [f.strip() for f in args.fields.split(",") if f.strip()]
    elif (args.domain, args.dataset) == (ORLANDO_DOMAIN, ORLANDO_DATASET):
        fields = list(ORLANDO_FIELDS)
    else:
        fields = None

    extra = list(args.extra)
    type_field: str | None = args.type_field
    types: list[str | None] = list(args.types)
    if args.preset:
        type_field, preset_type, preset_extra = ORLANDO_PRESETS[args.preset]
        extra += preset_extra
        if preset_type:
            types.append(preset_type)
    if not types:
        types = [None]

    client = client or SocrataClient(args.domain, args.dataset, app_token=args.app_token)
    raw = []
    for t in types:
        where = build_where(
            date_field=args.date_field, window=window, type_field=type_field, type_value=t, extra=extra
        )
        raw.extend(client.iter_rows(where=where, select=fields, order=f"{args.date_field} DESC,{args.key}"))

    rows = normalize(raw, fields, date_fields=[args.date_field])
    rows = sort_rows(dedupe(rows, args.key), args.date_field, args.key)
    total = len(rows)
    if args.limit is not None:
        rows = rows[: args.limit]

    summary = {
        "source": client.base_url,
        "window": [window.start.isoformat(), window.end.isoformat()],
        "fetched": len(raw),
        "unique": total,
        "duplicates_removed": len(raw) - total,
        "written": len(rows),
    }
    if not rows and not args.allow_empty:
        print(json.dumps(summary), file=sys.stderr)
        print(
            "no permits matched; nothing written (use --allow-empty to write a header-only CSV)",
            file=sys.stderr,
        )
        return 1

    cols = fields or (list(rows[0]) if rows else [])
    summary["csv"] = str(write_csv(rows, args.output, cols))
    if args.markdown:
        title = f"Permits issued {window.start} to {window.end}"
        md = Path(args.markdown)
        md.parent.mkdir(parents=True, exist_ok=True)
        md.write_text(to_markdown(rows, cols, title=title), encoding="utf-8")
        summary["markdown"] = str(md)
    print(json.dumps(summary))
    return 0


def main() -> None:  # pragma: no cover
    sys.exit(run())


if __name__ == "__main__":  # pragma: no cover
    main()
