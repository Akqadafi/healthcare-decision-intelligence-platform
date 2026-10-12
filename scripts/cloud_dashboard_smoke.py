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
    page.get_by_text("Explore counties", exact=True).click()
    expect(page.get_by_role("heading", name="Where to invest first")).to_be_visible()
    expect(page.get_by_text("75.1 / 100", exact=True)).to_be_visible()
    expect(page.get_by_test_id("stMetric").filter(has_text="Counties in view")).to_contain_text(
        "15"
    )
    page.screenshot(path=str(args.evidence / "dashboard.png"))
    # The accessibility grid must expose the numeric score, not 7,510%.
    expect(
        page.locator("table[role=grid]").filter(has_text="priority_tier").locator("#glide-cell-3-0")
    ).to_have_text("75.1")
    page.get_by_role("tab", name="Map & county profile").click()
    expect(page.get_by_text("County profile", exact=True)).to_be_visible()
    # The default is tile-free: actual Plotly point paths must render.
    expect(page.locator(".scatterlayer .point").first).to_be_visible()
    page.get_by_role("combobox", name="County profile", exact=True).click()
    page.get_by_role("option", name="Santa Cruz", exact=True).click()
    page.get_by_role("tab", name="Allocation scenario").click()
    expect(page.get_by_role("heading", name="Resource allocation scenario")).to_be_visible()
    capacity = page.get_by_role("slider", name="Operational capacity (counties)")
    capacity.press("Home")
    capacity.press("ArrowRight")
    page.get_by_role("heading", name="Resource allocation scenario").click()
    expect(capacity).to_have_attribute("aria-valuenow", "2")
    expect(page.get_by_test_id("stMetric").filter(has_text="Recommended counties")).to_contain_text(
        "2"
    )
    page.get_by_text("Metrics & methods", exact=True).click()
    expect(page.get_by_role("heading", name="Metrics glossary and scoring methods")).to_be_visible()
    page.get_by_text("Trust center", exact=True).click()
    expect(page.get_by_role("heading", name="Data checks and modeling assumptions")).to_be_visible()
    page.screenshot(path=str(args.evidence / "trust-center.png"))
    page.get_by_text("Explore counties", exact=True).click()
    page.get_by_role("tab", name="Allocation scenario").click()
    expect(page.get_by_role("slider", name="Operational capacity (counties)")).to_have_attribute(
        "aria-valuenow", "2"
    )
    page.get_by_role("tab", name="Map & county profile").click()
    expect(page.get_by_role("combobox", name="County profile", exact=True)).to_contain_text(
        "Santa Cruz"
    )
    page.screenshot(path=str(args.evidence / "county-locations.png"))
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
