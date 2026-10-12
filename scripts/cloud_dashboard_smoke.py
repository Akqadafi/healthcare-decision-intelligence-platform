"""Exercise the deployed Streamlit UI and save a screenshot; needs Playwright Chromium."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--url", required=True)
parser.add_argument("--evidence", type=Path, required=True)
args = parser.parse_args()
args.evidence.mkdir(parents=True, exist_ok=True)
with sync_playwright() as playwright:
    browser = playwright.chromium.launch()
    page = browser.new_page(viewport={"width": 1440, "height": 1000})
    page.set_default_timeout(60000)
    page.goto(args.url, wait_until="domcontentloaded")
    expect(page.get_by_role("heading", name="What this dashboard looks at")).to_be_visible()
    page.get_by_role("radio", name="Explore counties", exact=True).check()
    expect(page.get_by_role("heading", name="Where to invest first")).to_be_visible()
    expect(page.get_by_text("75.1 / 100", exact=True)).to_be_visible()
    expect(page.get_by_test_id("stMetric").filter(has_text="Counties in view")).to_contain_text(
        "15"
    )
    page.screenshot(path=str(args.evidence / "dashboard.png"))
    page.get_by_role("tab", name="Map & county profile").click()
    expect(page.get_by_text("County profile", exact=True)).to_be_visible()
    page.get_by_role("tab", name="Allocation scenario").click()
    expect(page.get_by_role("heading", name="Resource allocation scenario")).to_be_visible()
    page.get_by_role("radio", name="Metrics & methods", exact=True).check()
    expect(page.get_by_role("heading", name="Metrics glossary and scoring methods")).to_be_visible()
    page.get_by_role("radio", name="Trust center", exact=True).check()
    expect(page.get_by_role("heading", name="Data checks and modeling assumptions")).to_be_visible()
    page.screenshot(path=str(args.evidence / "trust-center.png"))
    browser.close()
(args.evidence / "browser-checks.json").write_text(
    json.dumps(
        {
            "status": "passed",
            "url": args.url,
            "apache_score": 75.1,
            "views": ["start", "ranking", "map", "scenario", "methods", "trust"],
        }
    ),
    encoding="utf-8",
)
