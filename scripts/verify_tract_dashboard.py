"""Verify tract controls, downloads, and the Apache walkthrough in a real browser."""

import argparse
import hashlib
import json
import time
from pathlib import Path

import pandas as pd
from playwright.sync_api import expect, sync_playwright


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8502")
    parser.add_argument("--channel", default=None)
    args = parser.parse_args()
    expect.set_options(timeout=60000)
    output = Path("docs/evidence/tract-dashboard")
    output.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    with sync_playwright() as p:
        browser = p.chromium.launch(channel=args.channel, headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1100})
        page.set_default_timeout(60000)
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        try:
            page.goto(args.url, wait_until="domcontentloaded")
            page.get_by_text("Explore census tracts", exact=True).click()
            expect(page.get_by_role("heading", name="Explore census tracts", exact=True)
                   ).to_be_visible()
            shown = page.get_by_test_id("stMetric").filter(
                has=page.get_by_text("Tracts shown", exact=True))
            expect(shown).to_contain_text("1,765")
            page.locator(".maplibregl-canvas").first.wait_for()
            page.screenshot(path=str(output / "overview.png"))
            multi = page.get_by_test_id("stMultiSelect")
            clear = multi.get_by_role("button", name="Clear all", exact=True)
            if clear.count():
                clear.click()
                expect(shown).to_contain_text("0")
                county = page.get_by_role("combobox", name="Counties", exact=True)
                county.fill("Apache")
                county.press("ArrowDown")
                county.press("Enter")
                county.press("Escape")
            else:
                for name in ["Cochise", "Coconino", "Gila", "Graham", "Greenlee", "La Paz",
                             "Maricopa", "Mohave", "Navajo", "Pima", "Pinal", "Santa Cruz",
                             "Yavapai", "Yuma"]:
                    multi.get_by_role("button", name=f"Remove {name}", exact=True).click()
            expect(shown).to_contain_text("18")
            expect(page.get_by_role("combobox", name="First tract", exact=True)
                   ).to_have_value("04001942600")
            expect(page.get_by_role("combobox", name="Comparison tract", exact=True)
                   ).to_have_value("04001942700")
            page.get_by_test_id("stPlotlyChart").scroll_into_view_if_needed()
            page.screenshot(path=str(output / "apache.png"))
            method = page.get_by_role("combobox", name="Clustering method", exact=True)
            method.fill("Ward")
            method.press("ArrowDown")
            method.press("Enter")
            expect(page.get_by_text("Exploratory comparison:", exact=False)).to_be_visible()
            method.fill("K-means")
            method.press("ArrowDown")
            method.press("Enter")
            expect(page.get_by_text("This model passed", exact=False)).to_be_visible()
            page.get_by_role("tab", name="Downloads & help", exact=True).click()
            for label, filename in [("Download filtered tract data", "apache.csv"),
                                     ("Download study receipt", "receipt.json")]:
                with page.expect_download() as result:
                    page.get_by_role("button", name=label, exact=True).click()
                result.value.save_as(output / filename)
            receipt = json.loads((output / "receipt.json").read_text())
            payload = (output / "apache.csv").read_bytes()
            assert hashlib.sha256(payload).hexdigest() == receipt["csv_sha256"]
            frame = pd.read_csv(output / "apache.csv", dtype={"tractfips": str})
            assert len(frame) == receipt["rows"] == 18
            assert receipt["model"] == "kmeans_k2"
            assert frame.set_index("tractfips").loc["04001942600", "diabetes_pct"] == 21.5
            page.get_by_role("button", name="Download model comparisons", exact=True
                             ).scroll_into_view_if_needed()
            expect(page.get_by_test_id("stApp")).to_have_attribute(
                "data-test-script-state", "notRunning")
            page.screenshot(path=str(output / "downloads.png"))
            assert not errors, errors
            (output / "browser-checks.json").write_text(json.dumps({
                "status": "passed", "rows": 18, "model": "kmeans_k2",
                "csv_hash_verified": True, "page_errors": errors,
                "elapsed_seconds": round(time.monotonic() - started, 1),
                "browser": browser.version,
            }, indent=2), encoding="utf-8")
        except Exception:
            page.screenshot(path=str(output / "failure.png"))
            raise
        finally:
            browser.close()
    print((output / "browser-checks.json").read_text())


if __name__ == "__main__":
    main()
