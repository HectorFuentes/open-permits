"""open-permits: pull building permits from Socrata open-data portals into clean CSV/Markdown."""

__version__ = "0.1.0"

from .query import Window, build_where
from .report import dedupe, normalize, sort_rows, to_markdown, write_csv
from .socrata import SocrataClient

__all__ = [
    "SocrataClient",
    "Window",
    "build_where",
    "dedupe",
    "normalize",
    "sort_rows",
    "to_markdown",
    "write_csv",
    "__version__",
]
