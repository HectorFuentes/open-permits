import urllib.error

import pytest

from open_permits.socrata import SocrataClient

from .conftest import FakeFetch


def test_url_and_headers():
    c = SocrataClient("https://data.example.gov/", "abcd-1234", app_token="tok", fetch=lambda u, h: [])
    assert c.base_url == "https://data.example.gov/resource/abcd-1234.json"
    assert c.headers["X-App-Token"] == "tok"
    url = c.url({"$where": "a='b c'", "$select": None})
    assert url.endswith("?%24where=a%3D%27b%20c%27")


def test_iter_rows_paginates(plumbing):
    fake = FakeFetch({"": [plumbing[:2], plumbing[2:4], plumbing[4:5]]})
    c = SocrataClient("d", "x", fetch=fake)
    rows = list(c.iter_rows(where="w", page_size=2))
    assert len(rows) == 5
    assert [call["$offset"] for call in fake.calls] == ["0", "2", "4"]


def test_retries_transient_errors(plumbing):
    attempts = []

    def flaky(url, headers):
        attempts.append(url)
        if len(attempts) < 3:
            raise urllib.error.HTTPError(url, 429, "slow down", None, None)
        return plumbing

    c = SocrataClient("d", "x", fetch=flaky, backoff=0)
    assert c.get({}) == plumbing
    assert len(attempts) == 3


def test_does_not_retry_client_errors():
    def bad(url, headers):
        raise urllib.error.HTTPError(url, 400, "bad query", None, None)

    with pytest.raises(urllib.error.HTTPError):
        SocrataClient("d", "x", fetch=bad, backoff=0).get({})


def test_rejects_non_list_payload():
    with pytest.raises(ValueError):
        SocrataClient("d", "x", fetch=lambda u, h: {"error": True}).get({})
