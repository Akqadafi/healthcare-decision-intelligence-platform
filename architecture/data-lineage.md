# Data lineage

| Output field | Transformation | Upstream source |
|---|---|---|
| `county_fips` | Left-padded 5-character code | CDC `CountyFIPS` |
| `health_burden_score` | Weighted within-state percentiles | CDC obesity, diabetes, blood pressure, physical and mental health |
| `sdoh_score` | Poverty, food insecurity, uninsured, and inverse income percentiles | Census ACS + CDC PLACES |
| `access_score` | Transportation, inverse checkup rate, inverse hospital density | CDC + CMS |
| `hospital_gap_score` | Inverse 1–5 rating; 60 when rating evidence is insufficient | CMS |
| `total_priority_score` | 35% health + 25% SDOH + 25% access + 15% hospital gap | Derived domains |
| `recommended_action` | Documented rules based on dominant domain and thresholds | Gold mart |

## Processing states

1. **Source:** agency API response.
2. **Snapshot:** minimal, auditable public fields committed for reproducibility.
3. **Normalized:** canonical types, names, FIPS, and county match key.
4. **Gold:** one row per county with scores, evidence status, and recommended action.
5. **Presentation:** filtered rankings, map, profile, scenario output, and trust checks.

The build manifest records timestamp, execution mode, row count, and quality status. API payloads
and transient raw files are excluded from Git.
