# Synthetic Arizona pilot fixtures

Run the implemented validation/comparison functions from the repository root:

```powershell
.\.venv\Scripts\python.exe scripts/workbench_demo.py
```

This prints a synthetic JSON comparison with rates, reasons, input hash, and row counts. It is a local calculation demo, not the planned upload interface or full study receipt. The parser currently requires canonical column names. A file with any invalid row is rejected as a whole.

Specification examples only. All numeric values are invented. County codes/names refer to real places, but the files contain no actual public-health or outreach observations.

`context_SYNTHETIC.csv` supplies four selected counties with synthetic January 2025 context. `outreach_SYNTHETIC.csv` supplies three service records. Maricopa intentionally has no service record; Coconino has an explicit zero.

Expected at need >= 20 and contacts per 1,000 residents < 2: Apache and Coconino flagged; Cochise outside thresholds; Maricopa unclassified. Three uploads match, with one public-context-only county. No people-served percentage can be inferred from contact counts.

See [the pilot specification](../../docs/ARIZONA_PILOT_SPEC.md). These files do not add upload support to the existing dashboard.
