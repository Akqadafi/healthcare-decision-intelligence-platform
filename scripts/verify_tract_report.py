"""Check a locally served analysis report; requires the CI Playwright tool."""

import argparse
import json
from pathlib import Path

from playwright.sync_api import sync_playwright


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8766/analysis.html")
    parser.add_argument("--channel", default=None)
    args = parser.parse_args()
    output = Path("docs/evidence/tract-study/models")
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel=args.channel, headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1000}, device_scale_factor=1)
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(args.url, wait_until="networkidle", timeout=60000)
        page.locator("#tract-study-3 canvas").first.wait_for(timeout=30000)
        assert page.locator(".js-plotly-plot").count() == 4
        assert not errors, errors
        page.screenshot(path=str(output / "analysis-overview.png"))
        for index in range(1, 4):
            page.locator(f"#tract-study-{index}").screenshot(
                path=str(output / f"analysis-chart-{index}.png"))
        print(json.dumps({"plots": 4, "page_errors": errors, "browser": browser.version}))
        browser.close()


if __name__ == "__main__":
    main()
