"""Check the dashboard and snapshot data inside the exact built container image."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd
from streamlit.testing.v1 import AppTest

from healthcare_di.config import GOLD_DIR, PROJECT_ROOT
from healthcare_di.quality import assert_quality

mart_file = GOLD_DIR / "mart_community_priority.csv"
mart = pd.read_csv(mart_file, dtype={"county_fips": str})
assert_quality(mart)
apache = mart.loc[mart["county_name"].eq("Apache")].iloc[0]
assert apache["rank"] == 1 and apache["total_priority_score"] == 75.1
app = AppTest.from_file(str(PROJECT_ROOT / "dashboard/app.py"), default_timeout=40).run()
for page in ["Start here", "Explore counties", "Explore census tracts",
             "Metrics & methods", "Trust center"]:
    app.sidebar.radio[0].set_value(page).run()
    assert not app.exception, (page, app.exception)
print(
    json.dumps(
        {
            "status": "passed",
            "counties": len(mart),
            "apache_score": 75.1,
            "mart_sha256": hashlib.sha256(mart_file.read_bytes()).hexdigest(),
            "pages": 5,
            "project_root": str(Path(PROJECT_ROOT)),
        },
        indent=2,
    )
)
