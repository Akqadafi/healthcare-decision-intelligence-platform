"""Pure CSV validation and descriptive comparison for the Arizona pilot.

No uploads are persisted and no network calls are made by this module.
"""

import csv
import hashlib
import io
import math
import re
from dataclasses import dataclass

AZ_FIPS = frozenset(
    f"04{code:03}" for code in [1, 3, 5, 7, 9, 11, 12, 13, 15, 17, 19, 21, 23, 25, 27]
)
MAX_BYTES = 10 * 1024 * 1024
MAX_ROWS = 100_000
FIELDS = ("county_fips", "reporting_month", "program", "contacts")


@dataclass(frozen=True)
class Issue:
    row: int
    field: str
    message: str


class ValidationError(ValueError):
    def __init__(self, issues):
        self.issues = tuple(issues)
        super().__init__("; ".join(f"Row {i.row}, {i.field}: {i.message}" for i in self.issues))


@dataclass(frozen=True)
class Study:
    counties: tuple[str, ...]
    month: str
    program: str
    need_threshold: float = 20
    activity_threshold: float = 2
    period_rationale: str = ""

    def __post_init__(self):
        if not self.counties or len(set(self.counties)) != len(self.counties):
            raise ValueError("Select a nonempty, unique county scope")
        if not set(self.counties) <= AZ_FIPS:
            raise ValueError("Only Arizona county FIPS are supported")
        if not valid_month(self.month):
            raise ValueError("Study month must be YYYY-MM")
        if not self.program.strip():
            raise ValueError("Program is required")
        if not math.isfinite(self.need_threshold) or not 0 <= self.need_threshold <= 100:
            raise ValueError("Need threshold must be between 0 and 100")
        if not math.isfinite(self.activity_threshold) or self.activity_threshold < 0:
            raise ValueError("Activity threshold must be finite and nonnegative")


def valid_month(value):
    return bool(re.fullmatch(r"[0-9]{4}-(0[1-9]|1[0-2])", value)) and value[:4] != "0000"


def parse_contacts(content: bytes, study: Study) -> dict:
    """Validate the canonical CSV template; error rows are 1-based CSV records.

    Any error blocks the entire input. Column mapping belongs to the later UI.
    """
    if len(content) > MAX_BYTES:
        raise ValidationError([Issue(0, "file", "File exceeds 10 MiB")])
    try:
        decoded = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValidationError([Issue(0, "file", "Use UTF-8 CSV")]) from exc
    if "\x00" in decoded:
        raise ValidationError([Issue(0, "file", "NUL bytes are not allowed")])
    reader = csv.reader(io.StringIO(decoded, newline=""), strict=True)
    issues, records, seen = [], [], {}
    try:
        header = next(reader, [])
        if len(header) != len(FIELDS) or set(header) != set(FIELDS):
            raise ValidationError([Issue(1, "header", "Use each required column exactly once")])
        for number, values in enumerate(reader, 2):
            if number - 1 > MAX_ROWS:
                raise ValidationError([Issue(number, "file", "Too many rows")])
            if len(values) != len(header):
                issues.append(Issue(number, "row", "Unexpected column count"))
                continue
            row = dict(zip(header, values, strict=True))
            fips = row["county_fips"]
            if fips not in study.counties:
                issues.append(Issue(number, "county_fips", "Unknown or out-of-scope county"))
            if row["reporting_month"] != study.month:
                issues.append(Issue(number, "reporting_month", "Must match the study month"))
            if row["program"] != study.program:
                issues.append(Issue(number, "program", "Must match the selected program"))
            count = row["contacts"]
            # Limit numeric magnitude as well as file size; avoid float overflow downstream.
            if not re.fullmatch(r"[0-9]{1,15}", count):
                issues.append(
                    Issue(number, "contacts", "Use a nonnegative integer, at most 15 digits")
                )
            else:
                row["contacts"] = int(count)
            key = (fips, row["reporting_month"], row["program"])
            if key in seen:
                issues.append(
                    Issue(number, "row", f"Duplicate key; first appears at row {seen[key]}")
                )
            seen[key] = number
            records.append(row)
    except csv.Error as exc:
        raise ValidationError([Issue(reader.line_num, "file", "Malformed CSV")]) from exc
    if not records and not issues:
        issues.append(Issue(2, "file", "At least one service record is required"))
    if issues:
        raise ValidationError(issues)
    return {"records": records, "sha256": hashlib.sha256(content).hexdigest()}


def finite_number(value):
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return number if math.isfinite(number) else None


def compare_contacts(content: bytes, context: list[dict], study: Study) -> dict:
    """Compare validated contacts to an explicitly selected county context.

    Context must contain exactly one row per selected county. Source metadata and
    provenance are the caller's responsibility; this is not a full study receipt.
    """
    parsed = parse_contacts(content, study)
    codes = [row.get("county_fips") for row in context]
    if len(codes) != len(set(codes)) or set(codes) != set(study.counties):
        raise ValueError("Context must contain exactly one row per selected county")
    periods = {row.get("observation_month", "") for row in context}
    if any(not isinstance(period, str) or not valid_month(period) for period in periods):
        raise ValueError("Context observation months must be YYYY-MM")
    if periods != {study.month} and not study.period_rationale.strip():
        raise ValueError("Period mismatch requires a recorded rationale")
    contacts = {row["county_fips"]: row["contacts"] for row in parsed["records"]}
    results = []
    for row in sorted(context, key=lambda item: item["county_fips"]):
        fips = row["county_fips"]
        count = contacts.get(fips)
        population = finite_number(row.get("resident_population"))
        need = finite_number(row.get("need_percent"))
        reasons = []
        if count is None:
            reasons.append("missing_service_record")
        if population is None or population <= 0 or not population.is_integer():
            reasons.append("invalid_population")
        if need is None or not 0 <= need <= 100:
            reasons.append("invalid_need_measure")
        rate = (
            count / population * 1000
            if count is not None and "invalid_population" not in reasons
            else None
        )
        flag = None if reasons else need >= study.need_threshold and rate < study.activity_threshold
        results.append(
            {
                "county_fips": fips,
                "contacts": count,
                "need_percent": need,
                "resident_population": population,
                "contacts_per_1000": rate,
                "investigate": flag,
                "reasons": reasons,
            }
        )
    return {
        "results": results,
        "input_sha256": parsed["sha256"],
        "study_month": study.month,
        "observation_months": sorted(periods),
        "period_rationale": study.period_rationale,
        "thresholds": {
            "need_at_least": study.need_threshold,
            "activity_below": study.activity_threshold,
        },
        "counts": {
            "uploaded": len(contacts),
            "matched": len(contacts),
            "rejected": 0,
            "context_only": len(context) - len(contacts),
            "classifiable": sum(row["investigate"] is not None for row in results),
            "unclassifiable": sum(row["investigate"] is None for row in results),
            "flagged": sum(row["investigate"] is True for row in results),
        },
    }
