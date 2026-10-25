"""Ready-made settings for the City of Orlando building-permit dataset.

Dataset: https://data.cityoforlando.net/d/ryhf-m453 (public, no key needed).
"""

from __future__ import annotations

ORLANDO_DOMAIN = "data.cityoforlando.net"
ORLANDO_DATASET = "ryhf-m453"
ORLANDO_DATE_FIELD = "issue_permit_date"
ORLANDO_KEY = "permit_number"
ORLANDO_FIELDS = [
    "permit_number",
    "application_type",
    "worktype",
    "permit_address",
    "issue_permit_date",
    "estimated_cost",
    "application_status",
    "neighborhood",
]

# name -> (type_field, type_value, extra clauses)
ORLANDO_PRESETS: dict[str, tuple[str | None, str | None, list[str]]] = {
    "plumbing": ("application_type", "Plumbing", []),
    "mechanical": ("application_type", "Mechanical Permit", []),
    "electrical": ("application_type", "Electrical", []),
    "building": ("application_type", "Building Permit", []),
    "roofing": (None, None, ["worktype='Roof'"]),
}
