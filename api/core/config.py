"""Backend configuration. Values are driven by environment variables."""
from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
DATA_PATH = Path(os.getenv("DATA_PATH", str(ROOT / "data")))
DATABASE_PATH = Path(os.getenv("DATABASE_PATH", str(DATA_PATH / "hospital360.duckdb")))
CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(",") if o.strip()]
APP_ENV = os.getenv("APP_ENV", "development")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
API_VERSION = "1.0.0"
API_PREFIX = "/api/v1"
MAX_PAGE_SIZE = 5000
DEFAULT_PAGE_SIZE = 50
MAX_EXPORT_ROWS = 5000
