# HRSA health-center layer — version 1.2.0

## Use the layer

1. Open **Explore census tracts** and choose a county, such as Apache.
2. In **Map & tract details**, check **Show HRSA health centers**. Permanent active
   service-delivery sites appear as black points. Community colors remain unchanged.
3. Use **Inspect a health center** to select a facility. Its point is highlighted in
   yellow and the map zooms to it. Read its address, phone and location type below
   the map. Choose **Choose a facility** again to return to the overview.
4. Optionally include mobile and seasonal sites. Purple points represent listed
   mobile addresses; brown points represent seasonal sites. Neither establishes
   current operations. The location type is also in each marker's hover text.
5. Open **Health-center table and source** for a map-independent list and source links.

Example question: Which HRSA-listed facilities are in Apache County while I explore
tract health indicators? Start the Apache tutorial and enable the layer. Moving to
the diabetes >=20% step narrows tracts but leaves facilities in Apache visible.
Facility coverage is county-scoped, not clipped to displayed tract polygons.
This prevents a tract indicator filter from hiding facilities elsewhere in the county.
No cross-county proximity search, distance or service-area calculation is performed.

A facility nearby does not establish capacity, appointments, affordability,
eligibility, travel access or unmet need. This is not a directory of all providers.
Confirm services with the provider. Census estimates and facility records describe
different time periods. No facility features enter clustering or county scores.

## Data and reproducibility

Source: [HRSA Health Care Service Delivery Sites GIS layer](https://gisportal.hrsa.gov/server/rest/services/HealthCareFacilities/PrimaryHealthCareFacilities_FS/MapServer/0).
Official locator: https://findahealthcenter.hrsa.gov/.

The November 1, 2026 UTC retrieval contains 264 Arizona records: 208 permanent,
30 mobile and 26 seasonal. All are labeled Active by HRSA at retrieval.
Only service-delivery and administrative/service-delivery types are displayed.
HRSA does not expose a dataset-update date in this layer's metadata; the app
explicitly distinguishes retrieval date from source freshness.

`docs/evidence/hrsa/arizona_sites.json` retains requested source fields and point
geometry. `manifest.json` records the endpoint, query, UTC retrieval, row count,
type counts and SHA-256. No API key or new runtime dependency is required.

Refresh manually with `python scripts/fetch_hrsa_sites.py`. The script rejects API
errors, truncated responses, count mismatches, duplicate/missing IDs, non-Arizona
states and unsupported county FIPS. Coordinates outside a broad Arizona bounding
box or missing coordinates are retained in the table but omitted from the map.
This bounding-box check does not prove a point's county or tract location; county
filtering uses HRSA's county code, not a spatial join. Source geocoding descriptions
are preserved, including approximate ZIP-level matches. Review new counts before
committing a refreshed snapshot. No refresh occurs during a user's session.

The layer fails independently: a missing or corrupted snapshot displays a warning
without preventing tract exploration. Tract downloads remain tract data; the HRSA
layer has separate provenance and is not a joined tract variable.

## Verification

Automated checks cover bundled snapshot integrity, permanent-only filtering,
county scope, missing coordinates, selection clearing when counties change,
empty selections and unchanged tract counts when the overlay is enabled.
Release CI and live deployment verification are recorded in the release notes.
