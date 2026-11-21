"""Capture Phase 0 BEFORE screenshots for UI redesign audit."""
from __future__ import annotations
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:3000"
PAGES = [
    ("overview", "/overview"),
    ("hospital-comparison", "/hospitals"),
    ("hospital-profile", "/hospitals/H01"),
    ("appointments", "/appointments"),
    ("inpatient", "/inpatient"),
    ("finance", "/finance"),
    ("claims", "/claims"),
    ("data-quality", "/data-quality"),
    ("explorer", "/explorer"),
    ("pipeline", "/pipeline"),
    ("kpi-glossary", "/kpi-glossary"),
]
VIEWPORTS = [(1440, 900, "1440"), (390, 844, "390")]

def main() -> int:
    out = Path("docs/ui/before")
    out.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for w, h, label in VIEWPORTS:
            context = browser.new_context(viewport={"width": w, "height": h})
            page = context.new_page()
            for name, route in PAGES:
                url = f"{BASE}{route}"
                try:
                    page.goto(url, wait_until="networkidle", timeout=60000)
                    page.wait_for_timeout(1500)
                    path = out / f"{name}-{label}.png"
                    page.screenshot(path=str(path), full_page=True)
                    print(f"ok {path}")
                except Exception as e:
                    print(f"fail {name} {label}: {e}")
            context.close()
        browser.close()
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
