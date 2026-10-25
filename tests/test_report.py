from open_permits.presets import ORLANDO_FIELDS
from open_permits.report import dedupe, normalize, sort_rows, to_markdown, write_csv


def test_normalize_trims_dates_and_fills_missing(plumbing):
    rows = normalize(plumbing + [{"permit_number": "X1"}], ORLANDO_FIELDS, ["issue_permit_date"])
    assert rows[0]["issue_permit_date"] == "2026-10-23"
    assert rows[-1]["permit_address"] == ""
    assert list(rows[0]) == ORLANDO_FIELDS


def test_normalize_infers_columns_and_skips_system_fields():
    rows = normalize([{"a": 1, ":id": "row-x"}, {"b": None, "loc": {"human_address": "1 Main"}}])
    assert list(rows[0]) == ["a", "b", "loc"]
    assert rows[1]["loc"] == "1 Main" and rows[0]["b"] == ""


def test_dedupe_keeps_first_and_drops_blank_keys(plumbing):
    rows = normalize(plumbing + plumbing[:2] + [{"permit_number": ""}], ORLANDO_FIELDS)
    out = dedupe(rows, "permit_number")
    assert len(out) == len(plumbing)
    assert len({r["permit_number"] for r in out}) == len(plumbing)


def test_sort_newest_then_higher_key(plumbing):
    rows = sort_rows(
        normalize(plumbing, ORLANDO_FIELDS, ["issue_permit_date"]), "issue_permit_date", "permit_number"
    )
    assert rows[0]["permit_number"] == "PLM2026-13036"
    assert rows[-1]["issue_permit_date"] == "2026-10-22"


def test_write_csv_round_trip(tmp_path, plumbing):
    rows = normalize(plumbing, ORLANDO_FIELDS)
    path = write_csv(rows, tmp_path / "sub" / "out.csv", ORLANDO_FIELDS)
    lines = path.read_text().splitlines()
    assert lines[0] == ",".join(ORLANDO_FIELDS)
    assert len(lines) == len(plumbing) + 1


def test_markdown_escapes_pipes():
    md = to_markdown([{"a": "x|y", "b": "line\nbreak"}], title="T")
    assert md.startswith("# T\n")
    assert "x\\|y" in md and "line break" in md
