"""Guard against silent geography loss and identifier coercion in the source audit."""

import importlib.util
from pathlib import Path

import pandas as pd
import pytest

spec = importlib.util.spec_from_file_location(
    "tract_data_audit", Path(__file__).resolve().parents[1] / "scripts/tract_data_audit.py"
)
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


def test_extract_only_arizona_tracts_preserve_status_and_leading_zero(tmp_path):
    source = tmp_path / "table.dat"
    source.write_text(
        "GEO_ID|B19013_E001|B19013_M001\n"
        "0100000US|78538|176\n"
        "1400000US04001942600|250000+|***\n"
        "1500000US040019426001|42000|100\n"
        "1400000US06001942600|42000|100\n", encoding="utf-8"
    )
    result = audit.read_acs(source, "B19013")
    assert result.to_dict("records") == [{
        "tractfips": "04001942600", "B19013_E001": "250000+", "B19013_M001": "***"
    }]


@pytest.mark.parametrize("identifiers", [
    ["04001942600", "04001942600"], ["4001942600"], ["06001942600"]
])
def test_bad_or_duplicate_identifiers_rejected(identifiers):
    with pytest.raises(ValueError):
        audit.check_ids(pd.DataFrame({"tractfips": identifiers}), "tractfips")
