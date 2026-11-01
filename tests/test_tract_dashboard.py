from pathlib import Path

from streamlit.testing.v1 import AppTest

from healthcare_di.tract_serving import filter_view, load_study, model_view

ROOT = Path(__file__).resolve().parents[1]


def test_saved_filters_keep_assignments_and_exclusions():
    data, _, _, _, _ = load_study(ROOT / "docs/evidence/tract-study")
    view = model_view(data, "kmeans_k2")
    assert len(view) == 1765
    assert view.profile.eq("Excluded").sum() == 35
    filtered = filter_view(view, ["Apache"], "All groups", "diabetes_pct", (0, 100), True, True)
    assert len(filtered) == 18
    assert filtered.set_index("tractfips").profile.equals(
        view.set_index("tractfips").loc[filtered.tractfips, "profile"])
    assert filter_view(view, [], "All groups", "diabetes_pct", (0, 100), True, True).empty


def test_controls_switch_models_persist_and_handle_empty_results():
    app = AppTest.from_file(str(ROOT / "dashboard/app.py"), default_timeout=60).run()
    app.sidebar.radio[0].set_value("Explore census tracts").run()
    assert not app.exception
    assert app.metric[0].value == "1,765"
    assert not app.checkbox(key="_tract_filter_enabled").value
    assert app.slider(key="_tract_range").disabled
    assert any("what are these groups" in item.label for item in app.expander)
    assert any("identifiers, not rankings" in item.value for item in app.markdown)
    assert any("Group 1 ·" in item.value and "median diabetes" in item.value
               for item in app.markdown)
    app.selectbox(key="_tract_method").set_value("Ward hierarchical").run()
    assert any("did not pass" in item.value for item in app.warning)
    app.multiselect(key="_tract_counties").set_value(["Apache"]).run()
    assert app.metric[0].value == "18"
    app.sidebar.radio[0].set_value("Explore counties").run()
    assert not app.exception
    app.sidebar.radio[0].set_value("Explore census tracts").run()
    assert app.selectbox(key="_tract_method").value == "Ward hierarchical"
    assert app.multiselect(key="_tract_counties").value == ["Apache"]
    app.select_slider(key="_tract_k").set_value(6).run()
    assert any("Group 6 ·" in item.value for item in app.markdown)
    app.selectbox(key="_tract_group").set_value("Group 6").run()
    app.select_slider(key="_tract_k").set_value(2).run()
    assert app.selectbox(key="_tract_group").value == "All groups"
    app.multiselect(key="_tract_counties").set_value([]).run()
    assert any("No tracts match" in item.value for item in app.warning)
    assert not app.exception

def test_guided_apache_walkthrough():
    app = AppTest.from_file(str(ROOT / "dashboard/app.py"), default_timeout=60).run()
    app.sidebar.radio[0].set_value("Explore census tracts").run()
    def press(label):
        next(item for item in app.button if item.label == label).click().run()
        assert not app.exception
    press("Start guided example: Apache County")
    assert app.metric[0].value == "18"
    assert app.selectbox(key="_tract_method").value == "K-means"
    press("Next: focus on diabetes estimates")
    assert app.checkbox(key="_tract_filter_enabled").value
    assert tuple(app.slider(key="_tract_range").value) == (20.0, 100.0)
    data, _, _, _, _ = load_study(ROOT / "docs/evidence/tract-study")
    expected = filter_view(model_view(data, "kmeans_k2"), ["Apache"], "All groups",
                           "diabetes_pct", (20, 100), False, True)
    assert app.metric[0].value == str(len(expected))
    press("Next: interpret and save")
    assert any("You have learned" in item.value for item in app.success)
    press("Finish walkthrough")
    assert "tract_tutorial_step" not in app.session_state
    app.checkbox(key="_tract_filter_enabled").uncheck().run()
    assert not app.exception
    assert app.metric[0].value == "18"
    assert app.slider(key="_tract_range").disabled
    assert tuple(app.slider(key="_tract_range").value) == (20.0, 100.0)
    app.checkbox(key="_tract_filter_enabled").check().run()
    assert app.metric[0].value == str(len(expected))
