"""Minimal, dependency-free client for the Socrata SODA 2.x API."""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Iterator
from typing import Any

Fetcher = Callable[[str, dict[str, str]], Any]

RETRY_STATUS = {403, 429, 500, 502, 503, 504}


def _default_fetch(url: str, headers: dict[str, str], timeout: float = 60.0) -> Any:
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.load(resp)


class SocrataClient:
    """Read rows from one Socrata dataset, e.g. ``data.cityoforlando.net`` / ``ryhf-m453``.

    ``fetch`` can be swapped out (tests pass a fake that serves recorded JSON).
    """

    def __init__(
        self,
        domain: str,
        dataset: str,
        *,
        app_token: str | None = None,
        fetch: Fetcher | None = None,
        retries: int = 4,
        backoff: float = 3.0,
        user_agent: str = "open-permits/0.1 (+https://github.com/HectorFuentes/open-permits)",
    ) -> None:
        domain = domain.removeprefix("https://").removeprefix("http://").strip("/")
        self.base_url = f"https://{domain}/resource/{dataset}.json"
        self.headers = {"Accept": "application/json", "User-Agent": user_agent}
        if app_token:
            self.headers["X-App-Token"] = app_token
        self._fetch = fetch or _default_fetch
        self.retries = max(1, retries)
        self.backoff = backoff

    def url(self, params: dict[str, Any]) -> str:
        clean = {k: str(v) for k, v in params.items() if v is not None and v != ""}
        if not clean:
            return self.base_url
        return self.base_url + "?" + urllib.parse.urlencode(clean, quote_via=urllib.parse.quote)

    def get(self, params: dict[str, Any]) -> list[dict[str, Any]]:
        url = self.url(params)
        for attempt in range(self.retries):
            try:
                data = self._fetch(url, self.headers)
            except urllib.error.HTTPError as exc:
                if attempt == self.retries - 1 or exc.code not in RETRY_STATUS:
                    raise
                time.sleep(self.backoff * (attempt + 1))
                continue
            if not isinstance(data, list):
                raise ValueError(f"expected a JSON array from {url}, got {type(data).__name__}")
            return data
        raise RuntimeError("unreachable")  # pragma: no cover

    def iter_rows(
        self,
        *,
        where: str | None = None,
        select: list[str] | None = None,
        order: str | None = None,
        page_size: int = 1000,
    ) -> Iterator[dict[str, Any]]:
        """Yield every matching row, following ``$offset`` pagination."""
        offset = 0
        while True:
            batch = self.get(
                {
                    "$select": ",".join(select) if select else None,
                    "$where": where,
                    "$order": order,
                    "$limit": page_size,
                    "$offset": offset,
                }
            )
            yield from batch
            if len(batch) < page_size:
                return
            offset += len(batch)
