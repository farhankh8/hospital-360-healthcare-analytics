"""HOSPITAL 360 ETL + analytics package.

Bronze -> Silver -> Quality -> Gold -> DuckDB, with quarantine and manifests.

Importing this package guarantees that the project root is on ``sys.path`` so
that ``generator.config`` and ``generator.schema`` can be used by every module
regardless of whether the code is invoked as ``python -m etl.pipeline`` or
imported from a notebook/test.
"""
from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

__all__ = ["PROJECT_ROOT"]
