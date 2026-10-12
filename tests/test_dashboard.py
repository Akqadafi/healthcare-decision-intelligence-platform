import json
from pathlib import Path

from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]


def app():
    return AppTest.from_file(str(ROOT / "dashboard/app.py"), default_timeout=40).run()


def test_scenario_and_county_survive_navigation():
    dashboard = app()
    dashboard.sidebar.radio[0].set_value("Explore counties").run()
    dashboard.slider(key="_budget").set_value(100_000).run()
    dashboard.slider(key="_capacity").set_value(2).run()
    dashboard.selectbox(key="_county").set_value("Santa Cruz").run()
    choice = dashboard.selectbox(key="_intervention").options[-1]
    dashboard.selectbox(key="_intervention").set_value(choice).run()
    for page in ["Start here", "Metrics & methods", "Trust center"]:
        dashboard.sidebar.radio[0].set_value(page).run()
        assert not dashboard.exception
    dashboard.sidebar.radio[0].set_value("Explore counties").run()
    assert dashboard.slider(key="_budget").value == 100_000
    assert dashboard.slider(key="_capacity").value == 2
    assert dashboard.selectbox(key="_intervention").value == choice
    assert dashboard.selectbox(key="_county").value == "Santa Cruz"
    assert not dashboard.exception


def test_filter_boundaries_and_display_contracts():
    dashboard = app()
    dashboard.sidebar.radio[0].set_value("Explore counties").run()
    score_tables = [
        table for table in dashboard.dataframe if "total_priority_score" in table.value.columns
    ]
    assert len(score_tables) == 2
    for table in score_tables:
        config = json.loads(table.proto.columns)
        assert config["total_priority_score"]["type_config"]["format"] == "%.1f"
    plots = [json.loads(plot.proto.spec) for plot in dashboard.get("plotly_chart")]
    location_plots = [
        plot
        for plot in plots
        if plot.get("layout", {}).get("xaxis", {}).get("title", {}).get("text") == "Longitude"
    ]
    assert len(location_plots) == 1
    assert sum(len(trace["text"]) for trace in location_plots[0]["data"]) == 15
    dashboard.sidebar.multiselect[0].set_value(["Critical"]).run()
    assert any("Showing 1 highest-ranked counties of 1" in item.value for item in dashboard.caption)
    dashboard.sidebar.multiselect[0].set_value([]).run()
    assert any("No counties match" in item.value for item in dashboard.warning)
    assert not dashboard.exception
    dashboard.sidebar.multiselect[0].set_value(["Critical", "High", "Elevated", "Monitor"]).run()
    dashboard.sidebar.number_input[0].set_value(5_000_000).run()
    assert any("No counties match" in item.value for item in dashboard.warning)
    assert not dashboard.exception


def test_serving_cache_tracks_file_version_and_rejects_invalid_outputs(tmp_path, monkeypatch):
    from healthcare_di.pipeline import load_snapshots
    from healthcare_di.scoring import build_priority_mart

    mart = build_priority_mart(*load_snapshots())
    path = tmp_path / "mart_community_priority.csv"
    mart.to_csv(path, index=False)
    monkeypatch.setenv("HDIP_DATA_DIR", str(tmp_path))
    dashboard = app()
    dashboard.sidebar.radio[0].set_value("Explore counties").run()
    before = next(
        metric.value for metric in dashboard.metric if metric.label == "Population represented"
    )
    mart.loc[0, "population"] += 1
    mart.to_csv(path, index=False)
    dashboard.run()
    after = next(
        metric.value for metric in dashboard.metric if metric.label == "Population represented"
    )
    assert int(after.replace(",", "")) == int(before.replace(",", "")) + 1
    mart.drop(columns="county_fips").to_csv(path, index=False)
    dashboard.run()
    assert not dashboard.exception
    assert "county_fips" in dashboard.error[0].value
