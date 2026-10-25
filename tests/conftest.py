import json
import urllib.parse
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


def load(name):
    return json.loads((FIXTURES / name).read_text())


class FakeFetch:
    """Serves recorded Socrata JSON. ``pages`` maps a substring of $where -> list of pages."""

    def __init__(self, pages):
        self.pages = {k: list(v) for k, v in pages.items()}
        self.calls = []

    def __call__(self, url, headers):
        params = dict(urllib.parse.parse_qsl(urllib.parse.urlsplit(url).query))
        self.calls.append(params)
        where = params.get("$where", "")
        for needle, pages in self.pages.items():
            if needle in where:
                return pages.pop(0) if pages else []
        return []


@pytest.fixture
def plumbing():
    return load("orlando_plumbing_page.json")


@pytest.fixture
def mechanical():
    return load("orlando_mechanical_page.json")
