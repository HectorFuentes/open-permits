import csv
import json

from open_permits.cli import run
from open_permits.socrata import SocrataClient

from .conftest import FakeFetch


def client(fake):
    return SocrataClient("data.cityoforlando.net", "ryhf-m453", fetch=fake)


def test_preset_writes_sorted_deduped_csv_and_markdown(tmp_path, plumbing, capsys):
    fake = FakeFetch({"Plumbing": [plumbing + plumbing[:1]]})
    out, md = tmp_path / "p.csv", tmp_path / "p.md"
    code = run(
        [
            "--preset",
            "plumbing",
            "--since",
            "2026-10-19",
            "--until",
            "2026-10-23",
            "-o",
            str(out),
            "--markdown",
            str(md),
        ],
        client=client(fake),
    )
    assert code == 0
    summary = json.loads(capsys.readouterr().out)
    assert summary["fetched"] == 7 and summary["unique"] == 6 and summary["duplicates_removed"] == 1
    rows = list(csv.DictReader(out.open()))
    assert rows[0]["permit_number"] == "PLM2026-13036"
    assert "property_owner_name" not in rows[0]
    assert md.read_text().startswith("# Permits issued 2026-10-19 to 2026-10-23")
    assert "application_type='Plumbing'" in fake.calls[0]["$where"]


def test_multiple_types_are_queried_separately_and_merged(tmp_path, plumbing, mechanical, capsys):
    fake = FakeFetch({"Plumbing": [plumbing], "Mechanical": [mechanical]})
    out = tmp_path / "both.csv"
    code = run(
        [
            "--type",
            "Plumbing",
            "--type",
            "Mechanical Permit",
            "--since",
            "2026-10-19",
            "--until",
            "2026-10-23",
            "--limit",
            "4",
            "-o",
            str(out),
        ],
        client=client(fake),
    )
    assert code == 0
    assert len(fake.calls) == 2
    assert all("(" not in c["$where"] for c in fake.calls)
    summary = json.loads(capsys.readouterr().out)
    assert summary["unique"] == 9 and summary["written"] == 4


def test_roofing_preset_uses_worktype(tmp_path, capsys):
    fake = FakeFetch({})
    run(
        [
            "--preset",
            "roofing",
            "--days",
            "3",
            "--until",
            "2026-10-23",
            "-o",
            str(tmp_path / "r.csv"),
            "--allow-empty",
        ],
        client=client(fake),
    )
    where = fake.calls[0]["$where"]
    assert where.startswith("worktype='Roof' AND issue_permit_date >= '2026-10-21")


def test_empty_window_exits_1_and_writes_nothing(tmp_path, capsys):
    out = tmp_path / "none.csv"
    code = run(
        ["--preset", "plumbing", "--since", "2026-10-24", "--until", "2026-10-24", "-o", str(out)],
        client=client(FakeFetch({})),
    )
    assert code == 1 and not out.exists()
    assert "nothing written" in capsys.readouterr().err


def test_allow_empty_writes_header_only(tmp_path, capsys):
    out = tmp_path / "none.csv"
    code = run(
        ["--preset", "plumbing", "--days", "1", "--until", "2026-10-24", "-o", str(out), "--allow-empty"],
        client=client(FakeFetch({})),
    )
    assert code == 0
    assert out.read_text().strip().startswith("permit_number,application_type")


def test_other_dataset_selects_all_columns(tmp_path, capsys):
    rows = [{"record_id": "1", "issued": "2026-10-01T00:00:00.000", "kind": "Pool"}]
    fake = FakeFetch({"": [rows]})
    c = SocrataClient("data.example.gov", "abcd-1234", fetch=fake)
    out = tmp_path / "o.csv"
    run(
        [
            "--domain",
            "data.example.gov",
            "--dataset",
            "abcd-1234",
            "--date-field",
            "issued",
            "--key",
            "record_id",
            "--since",
            "2026-10-01",
            "--until",
            "2026-10-01",
            "-o",
            str(out),
        ],
        client=c,
    )
    assert "$select" not in fake.calls[0]
    assert next(csv.DictReader(out.open())) == {"record_id": "1", "issued": "2026-10-01", "kind": "Pool"}
