#!/usr/bin/env python3
"""Post-deploy smoke checks for HOSPITAL 360.

Usage:
  python scripts/smoke_deployed.py --api https://<api> --web https://<web>
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request


def check(name: str, fn):
    try:
        detail = fn()
        print(f"PASS {name}: {detail}")
        return True
    except Exception as exc:  # noqa: BLE001
        print(f"FAIL {name}: {exc}")
        return False


def fetch(url: str, timeout: int = 30, headers: dict[str, str] | None = None):
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # nosec B310 - user-supplied deploy URL
        body = resp.read()
        return resp.status, dict(resp.headers), body


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api", required=True, help="Backend base URL, e.g. https://api.example.com")
    parser.add_argument("--web", required=True, help="Frontend base URL, e.g. https://app.example.com")
    args = parser.parse_args()
    api = args.api.rstrip("/")
    web = args.web.rstrip("/")
    results = []

    def health():
        status, _, body = fetch(f"{api}/api/v1/health")
        payload = json.loads(body.decode("utf-8"))
        if status != 200 or payload.get("status") not in {"ok", "healthy"}:
            raise RuntimeError(f"status={status} payload={payload}")
        return f"status={status}"

    def hospitals():
        status, _, body = fetch(f"{api}/api/v1/hospitals?page=1&page_size=5")
        payload = json.loads(body.decode("utf-8"))
        rows = payload.get("data") or []
        if status != 200 or not rows:
            raise RuntimeError(f"status={status} rows={len(rows)}")
        return f"rows={len(rows)}"

    def overview():
        status, _, body = fetch(f"{api}/api/v1/overview/kpis?date_from=2025-01-01&date_to=2026-12-31")
        payload = json.loads(body.decode("utf-8"))
        data = payload.get("data") or {}
        if status != 200 or not data:
            raise RuntimeError(f"status={status} keys={len(data)}")
        return f"kpis={len(data)}"

    def dq():
        status, _, body = fetch(f"{api}/api/v1/data-quality/summary")
        payload = json.loads(body.decode("utf-8"))
        if status != 200 or not payload.get("data"):
            raise RuntimeError(f"status={status}")
        return "ok"

    def records():
        status, _, body = fetch(f"{api}/api/v1/appointments/records?page=1&page_size=5&date_from=2025-01-01&date_to=2026-12-31")
        payload = json.loads(body.decode("utf-8"))
        if status != 200 or "data" not in payload:
            raise RuntimeError(f"status={status}")
        return f"rows={len(payload.get('data') or [])}"

    def cors():
        status, headers, _ = fetch(f"{api}/api/v1/health", headers={"Origin": web})
        acao = headers.get("Access-Control-Allow-Origin") or headers.get("access-control-allow-origin")
        if status != 200:
            raise RuntimeError(f"status={status}")
        if acao not in {web, "*"}:
            raise RuntimeError(f"missing/unexpected Access-Control-Allow-Origin: {acao}")
        return f"acao={acao}"

    def web_home():
        status, _, body = fetch(web)
        text = body.decode("utf-8", errors="ignore").lower()
        if status != 200 or "hospital 360" not in text:
            raise RuntimeError(f"status={status} marker={'hospital 360' in text}")
        return f"status={status}"

    for name, fn in [("health", health), ("hospitals", hospitals), ("overview_kpis", overview), ("dq_summary", dq), ("records_page", records), ("cors", cors), ("web_home", web_home)]:
        results.append(check(name, fn))
    ok = all(results)
    print(f"RESULT={'PASS' if ok else 'FAIL'} {sum(results)}/{len(results)} checks passed")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
