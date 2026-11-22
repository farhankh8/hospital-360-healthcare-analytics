"""Capture required HOSPITAL 360 screenshots from a running local or deployed app.

Usage:
  python scripts/capture_screenshots.py --base-url http://127.0.0.1:3000 --out docs/screenshots
Requires: playwright installed (`pip install playwright` and `playwright install chromium`).
"""
from __future__ import annotations

import argparse
from pathlib import Path

from playwright.sync_api import sync_playwright

SHOTS = [
    ("01-overview.png", "/overview"),
    ("02-finance.png", "/finance"),
    ("03-data-quality.png", "/data-quality"),
    ("04-explorer.png", "/explorer"),
    ("05-patient-journey.png", "/patient-journey"),
    ("06-pipeline.png", "/pipeline"),
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:3000")
    parser.add_argument("--out", default="docs/screenshots")
    parser.add_argument("--width", type=int, default=1440)
    parser.add_argument("--height", type=int, default=900)
    args = parser.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    base = args.base_url.rstrip("/")

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": args.width, "height": args.height})
        for name, route in SHOTS:
            page.goto(f"{base}{route}", wait_until="networkidle", timeout=60000)
            page.wait_for_timeout(1500)
            page.screenshot(path=str(out / name), full_page=True)
            print(f"captured {out / name}")
        browser.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
