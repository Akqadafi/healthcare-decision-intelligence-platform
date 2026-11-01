import copy
import json
from pathlib import Path

import plotly.graph_objects as go
import pytest
from streamlit.testing.v1 import AppTest

from healthcare_di.health_center_view import add_markers
from healthcare_di.health_centers import filter_sites, load_sites, normalize_sites

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "docs/evidence/hrsa"


def test_snapshot_filters_coordinates_and_integrity(tmp_path):
    sites, manifest = load_sites(SNAPSHOT)
    assert len(sites) == manifest["rows"] == 264
    assert len(filter_sites(sites, sites.county_fips.unique())) == 208
    assert filter_sites(sites, []).empty
    apache = filter_sites(sites, ["04001"], True)
    assert not apache.empty and apache.county.eq("Apache").all()
    (tmp_path / "manifest.json").write_bytes((SNAPSHOT / "manifest.json").read_bytes())
    (tmp_path / "arizona_sites.json").write_bytes(b"{}")
    with pytest.raises(ValueError, match="checksum"):
        load_sites(tmp_path)


def test_bad_coordinates_are_retained_but_not_mapped():
    payload = json.loads((SNAPSHOT / "arizona_sites.json").read_text())
    one = {"features": [copy.deepcopy(payload["features"][0])]}
    one["features"][0]["geometry"] = {"x": 0, "y": 0}
    sites = normalize_sites(one)
    assert len(sites) == 1 and not sites.mappable.any()
    fig = go.Figure()
    add_markers(fig, (sites, sites.site_id.iloc[0], {}))
    assert len(fig.data) == 0
    one["features"].append(copy.deepcopy(one["features"][0]))
    with pytest.raises(ValueError, match="duplicate"):
        normalize_sites(one)


def test_overlay_filters_and_selection_do_not_change_tract_results():
    app = AppTest.from_file(str(ROOT / "dashboard/app.py"), default_timeout=60).run()
    app.sidebar.radio[0].set_value("Explore census tracts").run()
    app.multiselect(key="_tract_counties").set_value(["Apache"]).run()
    before = app.metric[0].value
    app.checkbox(key="hrsa_show").check().run()
    assert not app.exception and app.metric[0].value == before
    sites, manifest = load_sites(SNAPSHOT)
    expected = filter_sites(sites, ["04001"])
    selected = expected.site_id.iloc[0]
    app.selectbox(key="hrsa_selected").set_value(selected).run()
    assert not app.exception
    assert any(expected.iloc[0]['name'] in t.value for t in app.text)
    fig = go.Figure()
    add_markers(fig, (expected, selected, manifest))
    assert fig.data[-1].name == "Selected health center"
    app.multiselect(key="_tract_counties").set_value(["Cochise"]).run()
    assert not app.exception and app.selectbox(key="hrsa_selected").value is None
    app.multiselect(key="_tract_counties").set_value([]).run()
    assert not app.exception
    assert any("No matching sites" in i.value for i in app.info)
