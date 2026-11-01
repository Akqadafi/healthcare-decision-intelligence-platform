"""Session-scoped county CSV workflow; no uploaded content is cached or persisted."""

import csv
import hashlib
import json
import os
from dataclasses import asdict

import pandas as pd
import streamlit as st

from healthcare_di.config import PROJECT_ROOT
from healthcare_di.workbench import FIELDS, Study, ValidationError, compare_contacts
from healthcare_di.workbench_io import map_upload, package, read_upload

EXAMPLES = PROJECT_ROOT / "examples/workbench-pilot"
MEASURES = {
    "Uninsured adults": (
        "uninsured_rate", "2022-01", "2023-12",
        "CDC PLACES 2025 release; source manifest: 2022–2023 BRFSS",
        "Modeled crude prevalence among adults aged 18–64 without health insurance.",
    ),
    "Transportation barriers": (
        "transportation_barrier_rate", "2022-01", "2023-12",
        "CDC PLACES 2025 release; source manifest: 2022–2023 BRFSS",
        "Modeled adult prevalence of lack of reliable transportation.",
    ),
    "Poverty": (
        "poverty_rate", "2020-01", "2024-12",
        "ACS 2024 five-year release; observations cover 2020–2024",
        "Percentage of people below poverty level among those with poverty status determined.",
    ),
}


def reset():
    st.session_state["workbench_upload_epoch"] = (
        st.session_state.get("workbench_upload_epoch", 0) + 1
    )
    for key in list(st.session_state):
        if key.startswith("wb_"):
            del st.session_state[key]


def go(stage):
    st.session_state["wb_stage"] = stage


def prepare_context(mart, version, synthetic, label="Uninsured adults"):
    if synthetic:
        path = EXAMPLES / "context_SYNTHETIC.csv"
        with path.open(encoding="utf-8", newline="") as handle:
            context = list(csv.DictReader(handle))
        names = {row["county_fips"]: row["county_name"] for row in context}
        metadata = {
            "synthetic_context": True, "measure": "Example community indicator",
            "definition": "Invented values for learning how the comparison works.",
            "period_label": "January 2025 (invented example)",
            "population_label": "Invented resident population, January 2025",
            "source_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "activity_origin": "synthetic bundled example",
        }
    else:
        field, start, end, period, definition = MEASURES[label]
        names = dict(zip(mart["county_fips"].astype(str), mart["county_name"], strict=True))
        context = [
            {"county_fips": str(row["county_fips"]), "need_percent": row[field],
             "resident_population": row["population"], "period_start": start, "period_end": end}
            for row in mart.to_dict("records")
        ]
        path = PROJECT_ROOT / "data/metadata/source_manifest.json"
        metadata = {
            "synthetic_context": False, "measure": label, "variable": field,
            "definition": definition, "period_label": period,
            "population_label": "2023 total resident population from bundled CDC context",
            "source_manifest": json.loads(path.read_text()),
            "source_manifest_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "dataset_sha256": version,
            "uncertainty": "County source table does not retain uncertainty intervals.",
            "activity_origin": "user-supplied aggregate file; unverified",
        }
    return context, names, metadata


def use_example(mart, version):
    st.session_state["wb_highlight"] = False
    context, names, metadata = prepare_context(mart, version, True)
    st.session_state["wb_payload"] = {
        "raw": (EXAMPLES / "outreach_SYNTHETIC.csv").read_bytes(),
        "mapping": dict(zip(FIELDS, FIELDS, strict=True)),
        "context": context, "names": names, "metadata": metadata,
        "study": Study(tuple(names), "2025-01", "Demo outreach"),
    }
    go("results")


def canonical_counties(header, rows, mapping, names):
    """Resolve exact Arizona county names or valid codes; never fuzzy match."""
    positions = {field: header.index(column) for field, column in mapping.items()}
    lookup = {name.casefold(): code for code, name in names.items()}
    resolved = []
    for number, original in enumerate(rows, 2):
        row = list(original)
        value = row[positions["county_fips"]].strip()
        name = value.casefold()
        if name.endswith(" county"):
            name = name[:-7]
        code = value if value in names else lookup.get(name)
        if code is None:
            raise ValueError(
                f"Row {number}: county '{value}' was not recognized. "
                "Use an Arizona county name (such as Apache) or its five-digit code."
            )
        row[positions["county_fips"]] = code
        resolved.append(row)
    return map_upload(header, resolved, mapping)


def render_results():
    payload = st.session_state["wb_payload"]
    context, names = payload["context"], payload["names"]
    metadata = dict(payload["metadata"])
    synthetic = metadata["synthetic_context"]
    st.caption("3 of 3 · Your comparison")
    st.subheader("How does outreach vary across counties?")
    if synthetic:
        st.info("EXAMPLE · All numbers are invented. No real program is being evaluated.")
        with st.expander("What should I notice in this example?", expanded=True):
            st.write("Apache recorded 1 contact per 1,000 residents; Cochise recorded 4. "
                     "Coconino explicitly reported zero. Maricopa supplied no record, "
                     "so its activity is unknown—not zero.")
    else:
        st.caption(f"{payload['study'].program} · {payload['study'].month} · "
                   f"Comparing with {metadata['measure'].lower()}")
    highlight = st.toggle("Highlight counties using my criteria", value=False, key="wb_highlight",
                          help="Optional exploration. These are your criteria, not "
                               "recommended intervention or funding thresholds.")
    need, activity = 20.0, 2.0
    if highlight:
        st.caption("Starting values are illustrative. Choose criteria that suit your question.")
        a, b = st.columns(2)
        need = a.number_input("Community indicator at least (%)", 0.0, 100.0, 20.0,
                              key="wb_need")
        activity = b.number_input("Contacts per 1,000 below", 0.0, value=2.0, key="wb_activity")
    from dataclasses import replace

    study = replace(payload["study"], need_threshold=need, activity_threshold=activity)
    result = compare_contacts(payload["canonical"], context, study)
    count = result["counts"]
    a, b, c = st.columns(3)
    a.metric("Counties compared", len(context))
    b.metric("With activity records", count["matched"])
    c.metric("No activity record", count["context_only"])
    missing = [names[row["county_fips"]] for row in result["results"]
               if row["contacts"] is None]
    if missing:
        st.write("**No record supplied:** " + ", ".join(missing) + ". Activity is unknown.")
    display = pd.DataFrame({
        "County": [names[row["county_fips"]] for row in result["results"]],
        "Contacts": [row["contacts"] for row in result["results"]],
        "Contacts per 1,000 residents": [row["contacts_per_1000"] for row in result["results"]],
        metadata["measure"] + " (%)": [row["need_percent"] for row in result["results"]],
        "Record status": ["No record supplied" if row["contacts"] is None else
                          "Reported zero" if row["contacts"] == 0 else "Record supplied"
                          for row in result["results"]],
    })
    known = display.dropna(subset=["Contacts per 1,000 residents"])
    if not known.empty:
        st.bar_chart(known.set_index("County")[["Contacts per 1,000 residents"]],
                     horizontal=True, color="#68765A")
    st.caption("Contacts per 1,000 accounts for county population size. Repeat contacts may "
               "be included; this is not the percentage of people served. "
               "Counties without records are omitted from the chart.")
    if highlight:
        display["Meets my criteria"] = [
            "Unknown" if row["investigate"] is None else
            "Yes" if row["investigate"] else "No" for row in result["results"]
        ]
        st.write(f"**{count['flagged']} counties meet your criteria.** "
                 "This suggests places to investigate, not proof of unmet need.")
    st.dataframe(display, hide_index=True, column_config={
        "Contacts": st.column_config.NumberColumn(format="%d"),
        "Contacts per 1,000 residents": st.column_config.NumberColumn(format="%.2f"),
        metadata["measure"] + " (%)": st.column_config.NumberColumn(format="%.1f"),
    })
    with st.expander("Sources, dates and how to interpret this"):
        st.write(metadata["definition"])
        st.write("Community data: " + metadata["period_label"])
        st.write("Population used for rates: " + metadata["population_label"])
        st.write("Activity month: " + study.month)
        st.write("Different observation periods provide context, not a time trend. "
                 "Community estimates do not describe an individual. "
                 "Low recorded activity alone does not establish unmet need or program failure.")
        if study.period_rationale:
            st.write(study.period_rationale)
    metadata["highlight_enabled"] = highlight
    metadata["county_names"] = names
    metadata["implementation_sha256"] = hashlib.sha256(b"".join(
        (PROJECT_ROOT / "src/healthcare_di" / name).read_bytes()
        for name in ["workbench.py", "workbench_io.py", "workbench_view.py"]
    )).hexdigest()
    downloads = package(result, study, metadata, payload["raw"], payload["mapping"],
                        "How does our recorded outreach compare across counties?")
    import io
    import zipfile

    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as bundle:
        for filename, content in downloads.items():
            bundle.writestr(filename, content)
    st.download_button("Download comparison report", archive.getvalue(),
                       "outreach-comparison.zip", "application/zip", type="primary",
                       on_click="ignore")
    st.caption("Includes a readable brief, results spreadsheet, sources and processing details.")
    with st.expander("Technical details"):
        st.json({"counting_unit": "contacts, including repeat contacts",
                 "matching": result["counts"], "column_mapping": payload["mapping"]})
        st.download_button("Download receipt only", downloads["receipt.json"],
                           "receipt.json", "application/json", on_click="ignore")
    if not synthetic:
        st.button("Back to my spreadsheet", on_click=go, args=("upload",))


def render_upload(mart, version):
    st.caption("2 of 3 · Add your spreadsheet")
    st.subheader("Bring your county outreach counts")
    st.write("Use one row per county for one program and one month. "
             "We’ll add public community data for you.")
    st.caption("Public or non-sensitive aggregate data only. Files reach this server; "
               "do not include names, home addresses or patient records.")
    st.download_button("Get a starter CSV",
                       "County,Month,Program,Contacts\n",
                       "outreach-template.csv", "text/csv", on_click="ignore")
    with st.expander("What should my spreadsheet look like?"):
        st.dataframe(pd.DataFrame({"County": ["Apache", "Cochise"],
                                  "Month": ["2026-09", "2026-09"],
                                  "Program": ["Your program", "Your program"],
                                  "Contacts": [10, 0]}), hide_index=True)
        st.caption("Illustrative rows only. County names or five-digit county codes work. "
                   "Use 0 only for a reported zero. Leave out counties with no record. "
                   "Save Excel files as CSV (UTF-8). Maximum: 10 MiB and 100,000 rows.")
    epoch = st.session_state.get("workbench_upload_epoch", 0)
    uploaded = st.file_uploader("Choose your CSV", type=["csv"], key=f"wb_upload_{epoch}")
    if uploaded is None:
        st.info("Start by choosing a CSV above. "
                "Need a quick tour? Use Start over → Try an example.")
        return
    raw = uploaded.getvalue()
    try:
        header, rows = read_upload(raw)
    except ValueError as error:
        st.error(f"We couldn’t read this file: {error}")
        return
    digest = hashlib.sha256(raw).hexdigest()
    aliases = {
        "county_fips": ["county_fips", "county", "county_name"],
        "reporting_month": ["reporting_month", "month"],
        "program": ["program"],
        "contacts": ["contacts"],
    }
    normalized = {name.strip().casefold(): name for name in header}
    guessed = {field: next((normalized[key] for key in options if key in normalized), None)
               for field, options in aliases.items()}
    labels = {"county_fips": "County", "reporting_month": "Month",
              "program": "Program", "contacts": "Number of contacts"}
    mapping = {}
    needs_mapping = any(v is None for v in guessed.values())
    with st.expander("Check spreadsheet columns", expanded=needs_mapping):
        st.caption("Recognized columns are selected automatically. Change them only if needed.")
        for field in FIELDS:
            options = ["Choose a column"] + header
            mapping[field] = st.selectbox(labels[field], options,
                                          index=options.index(guessed[field])
                                          if guessed[field] else 0,
                                          key=f"wb_map_{digest}_{field}")
        st.dataframe(pd.DataFrame(rows[:5], columns=header), hide_index=True)
    if any(value not in header for value in mapping.values()):
        st.info("Choose the missing columns above so we know where to find your data.")
        return
    if len(set(mapping.values())) != len(FIELDS):
        st.error("Choose a different column for each field.")
        return
    excluded = [name for name in header if name not in mapping.values()]
    if excluded:
        st.caption("Not used in this comparison: " + ", ".join(excluded))
    periods = sorted({row[header.index(mapping["reporting_month"])] for row in rows})
    programs = sorted({row[header.index(mapping["program"])] for row in rows})
    if len(periods) != 1 or len(programs) != 1:
        st.warning("This first version compares one month and one program at a time. "
                   "Filter your spreadsheet to a single month and program, then upload it again.")
        return
    st.write(f"**{len(rows)} records found** · {programs[0]} · {periods[0]}")
    label = st.selectbox("What community condition would you like to compare?",
                         list(MEASURES), key="wb_measure",
                         help="Adds context beside outreach counts. "
                              "It does not score your program.")
    context, names, metadata = prepare_context(mart, version, False, label)
    with st.expander("Which counties should appear?"):
        counties = st.multiselect("Counties to compare", sorted(names, key=names.get),
                                  default=sorted(names, key=names.get),
                                  format_func=names.get, key="wb_counties")
        st.caption("All Arizona counties are included initially so missing records remain visible.")
    try:
        canonical = canonical_counties(header, rows, mapping, names)
        study = Study(tuple(counties), periods[0], programs[0],
                      period_rationale="Historical community indicators used as descriptive "
                                       "context for uploaded activity; no trend or causal claim.")
        selected = [row for row in context if row["county_fips"] in counties]
        compare_contacts(canonical, selected, study)
    except ValidationError as error:
        st.error("A few records need attention. Nothing has been removed or combined.")
        st.dataframe(pd.DataFrame([asdict(issue) for issue in error.issues]), hide_index=True)
        st.caption("Correct the listed rows and upload again. Duplicate counties need one "
                   "verified total; blank counts should not be changed to zero automatically.")
        return
    except ValueError as error:
        st.error(str(error))
        return
    st.caption(f"Community data: {metadata['period_label']}. "
               f"Population: {metadata['population_label']}.")
    accepted = st.checkbox(
        "I understand these dates differ; I’m using the community data as background.",
        key=f"wb_dates_{digest}_{label}")
    st.caption("This comparison cannot establish a time trend. Contacts may include repeat visits.")
    if st.button("Show my comparison", type="primary", disabled=not accepted):
        st.session_state["wb_highlight"] = False
        metadata["geography_resolution"] = (
            "Exact Arizona county name/code matching; trim surrounding whitespace; "
            "case-insensitive names; optional County suffix; no fuzzy matching"
        )
        st.session_state["wb_payload"] = {
            "raw": raw, "canonical": canonical, "mapping": mapping, "study": study,
            "context": selected, "names": names, "metadata": metadata,
        }
        go("results")
        st.rerun()


def render(mart, version):
    st.markdown("<style>section.hero {display:none}</style>", unsafe_allow_html=True)
    st.header("Compare outreach across communities")
    st.write("See your recorded outreach alongside community conditions—and take away "
             "a clear comparison report.")
    stage = st.session_state.get("wb_stage", "choose")
    if stage != "choose":
        st.button("Start over", on_click=reset)
    if stage == "choose":
        st.caption("1 of 3 · Choose how to begin")
        left, right = st.columns(2)
        with left, st.container(border=True):
            st.subheader("Try an example")
            st.write("No file needed. Explore four counties and learn what the results mean.")
            if st.button("Try an example", type="primary"):
                use_example(mart, version)
                payload = st.session_state["wb_payload"]
                payload["canonical"] = payload["raw"]
                st.rerun()
        with right, st.container(border=True):
            st.subheader("Use my outreach data")
            st.write("Upload county contact counts. We’ll connect them with public indicators.")
            st.button("Use my spreadsheet", on_click=go, args=("upload",))
        st.caption("Arizona counties · CSV files · No account required")
        with st.expander("What can this help me understand?"):
            st.write("Compare recorded activity across counties, notice missing records, "
                     "and examine community conditions. This is a planning conversation starter, "
                     "not a judgment of program performance or a prediction of health outcomes.")
    elif stage == "upload":
        if "HDIP_DATA_DIR" in os.environ:
            st.info("This dataset is not supported for uploads. Start over and try the example.")
        else:
            render_upload(mart, version)
    elif stage == "results" and "wb_payload" in st.session_state:
        render_results()
    else:
        reset()
        st.rerun()

