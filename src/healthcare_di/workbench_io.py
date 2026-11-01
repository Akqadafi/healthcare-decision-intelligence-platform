"""Bounded column mapping and safe, reproducible workbench downloads."""

import csv
import hashlib
import io
import json
from datetime import UTC, datetime

from healthcare_di.workbench import FIELDS, MAX_BYTES, MAX_ROWS


def read_upload(content):
    if len(content) > MAX_BYTES:
        raise ValueError("File exceeds 10 MiB")
    try:
        decoded = content.decode("utf-8-sig")
        if "\x00" in decoded:
            raise ValueError("NUL bytes are not allowed")
        reader = csv.reader(io.StringIO(decoded, newline=""), strict=True)
        header = next(reader, [])
        if not header or len(header) > 100 or any(not name.strip() for name in header):
            raise ValueError("Provide 1–100 named columns")
        if len(set(header)) != len(header):
            raise ValueError("Duplicate column names are not supported")
        rows = []
        for number, row in enumerate(reader, 2):
            if len(rows) >= MAX_ROWS:
                raise ValueError("Too many rows (maximum 100,000)")
            if len(row) != len(header):
                raise ValueError(f"Row {number}: unexpected column count")
            rows.append(row)
        if not rows:
            raise ValueError("At least one service record is required")
        return header, rows
    except (UnicodeDecodeError, csv.Error) as exc:
        raise ValueError("Use a well-formed UTF-8 CSV") from exc


def map_upload(header, rows, mapping):
    if set(mapping) != set(FIELDS) or len(set(mapping.values())) != len(FIELDS):
        raise ValueError("Map each required field to a different source column")
    if any(value not in header for value in mapping.values()):
        raise ValueError("Mapped column is not in the file")
    out = io.StringIO(newline="")
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(FIELDS)
    positions = [header.index(mapping[field]) for field in FIELDS]
    writer.writerows([[row[index] for index in positions] for row in rows])
    return out.getvalue().encode("utf-8")


def safe_cell(value):
    if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@")):
        return "'" + value
    return value


def export_csv(rows):
    out = io.StringIO(newline="")
    writer = csv.DictWriter(out, fieldnames=list(rows[0]), lineterminator="\n")
    writer.writeheader()
    writer.writerows({key: safe_cell(value) for key, value in row.items()} for row in rows)
    return out.getvalue().encode("utf-8")


def package(result, study, metadata, original, mapping, question):
    highlight = metadata.get("highlight_enabled", True)
    rows = [
        {**row, "reasons": "; ".join(row["reasons"])}
        for row in result["results"]
    ]
    if not highlight:
        for row in rows:
            row.pop("investigate", None)
    table = export_csv(rows)
    counts = dict(result["counts"])
    if not highlight:
        counts.pop("flagged", None)
    receipt = {
        "schema_version": "county-workbench-1",
        "question": question,
        "study": {
            "counties": list(study.counties), "month": study.month, "program": study.program,
            "counting_unit": "contacts including repeats",
            "highlight_enabled": highlight,
            "need_threshold": study.need_threshold if highlight else None,
            "activity_threshold": study.activity_threshold if highlight else None,
        },
        "metadata": metadata,
        "original_input_sha256": hashlib.sha256(original).hexdigest(),
        "canonical_input_sha256": result["input_sha256"],
        "column_mapping": mapping,
        "join_counts": counts,
        "period_rationale": study.period_rationale,
        "observation_periods": result["observation_periods"],
        "result_csv_sha256": hashlib.sha256(table).hexdigest(),
        "generated_utc": datetime.now(UTC).isoformat(),
        "csv_text_escaping": "Prefix apostrophe on formula-like text; input hash unchanged",
        "limitations": [
            "Low recorded activity is not proof of unmet need or program failure.",
            "Contacts may repeat; rates are not the percentage of eligible people served.",
            "Missing records are unknown, not zero.",
            "Settings do not reproduce results without matching input and source files.",
        ],
    }
    criteria = (
        f"Your criteria: indicator >= {study.need_threshold}%; "
        f"contacts/1,000 < {study.activity_threshold}. "
        f"{counts.get('flagged', 0)} counties meet these criteria."
        if highlight else "Optional highlighting was not used. No counties are flagged."
    )
    brief = (
        "# Outreach planning brief\n\n"
        + ("SYNTHETIC CONTEXT — invented populations and need values.\n\n"
           if metadata["synthetic_context"] else
           "PUBLIC CONTEXT WITH USER-SUPPLIED ACTIVITY — activity accuracy is unverified.\n\n")
        + f"Activity origin: {metadata['activity_origin']}.\n\n"
        + f"Question: {question}\n\nProgram: {study.program}\n\n"
        + f"Activity month: {study.month}\n\nMeasure: {metadata['measure']}\n\n"
        + f"Public/context period: {metadata['period_label']}\n\n"
        + f"Population: {metadata['population_label']}\n\n"
        + f"Comparison rationale: {study.period_rationale or 'Same synthetic month'}\n\n"
        + criteria + "\n\n"
        + f"Uploaded {counts['uploaded']}; matched {counts['matched']}; "
        + f"selected counties without records {counts['context_only']}; "
        + f"unclassified {counts['unclassifiable']}.\n\n"
        + "| County | Contacts | Contacts / 1,000 | Meets criteria |\n"
        + "|---|---:|---:|---|\n"
        + "".join(
            f"| {metadata.get('county_names', {}).get(row['county_fips'], row['county_fips'])} | "
            f"{row['contacts'] if row['contacts'] is not None else 'Unknown'} | "
            f"{row['contacts_per_1000'] if row['contacts_per_1000'] is not None else 'Unknown'} | "
            f"{str(row.get('investigate')) if highlight else 'Not used'} |\n"
            for row in rows
        )
        + "\nSee results.csv for all selected counties and receipt.json for sources, "
        + "definitions, hashes and settings.\n\n"
        + "\n".join("- " + note for note in receipt["limitations"]) + "\n"
    )
    return {
        "results.csv": table,
        "receipt.json": json.dumps(receipt, indent=2, allow_nan=False).encode(),
        "join-report.json": json.dumps({
            "status": "validated", "invalid_rows": [],
            "counts": counts,
            "counties_without_records": [
                row["county_fips"] for row in rows if row["contacts"] is None
            ],
        }, indent=2).encode(),
        "brief.md": brief.encode(),
    }
