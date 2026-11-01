"""Optional facility overlay and accessible facility details."""

from html import escape

import plotly.graph_objects as go
import streamlit as st

from healthcare_di.config import PROJECT_ROOT
from healthcare_di.health_centers import filter_sites, load_sites


def controls(county_fips):
    enabled = st.checkbox("Show HRSA health centers", key="hrsa_show",
                          help="Add facility locations in your selected counties. "
                          "These locations do not affect community groups or scores.")
    if not enabled:
        return None
    try:
        sites, manifest = load_sites(PROJECT_ROOT / "docs/evidence/hrsa")
    except (OSError, ValueError, KeyError) as error:
        st.warning(f"Health-center layer unavailable: {error}. Tract exploration still works.")
        return None
    st.caption("Sites follow Counties only. Community-group and indicator filters do not "
               "hide facilities. These are HRSA-listed sites, not all healthcare providers.")
    include_other = st.checkbox("Include mobile and seasonal sites", key="hrsa_other")
    if include_other:
        st.info("Mobile markers show listed addresses, not current vehicle locations or routes. "
                "Seasonal sites may not be open now. Confirm operations with the provider.")
    scoped = filter_sites(sites, county_fips, include_other)
    st.caption(f"{len(scoped)} active listed sites in selected counties · "
               f"{int(scoped.mappable.sum())} with usable map coordinates · "
               f"HRSA snapshot retrieved {manifest['retrieved_utc'][:10]} (UTC). "
               "Source update date not provided; retrieved does not mean recently updated.")
    st.warning("A nearby location does not establish appointments, capacity, affordability, "
               "eligibility or travel access. Check services with the provider. "
               "Facility points and tract estimates describe different time periods.")
    selected = None
    if scoped.empty:
        st.info("No matching sites in this snapshot. "
                "This is not evidence that no care is available.")
    else:
        choices = scoped.set_index("site_id")
        if st.session_state.get("hrsa_selected") not in choices.index:
            st.session_state["hrsa_selected"] = None
        selected = st.selectbox(
            "Inspect a health center", [None, *choices.index], key="hrsa_selected",
            format_func=lambda key: "Choose a facility" if key is None else
            f"{choices.loc[key, 'name']} · {choices.loc[key, 'city']} · {key[:8]}",
            help="Choose a facility to see its address and highlight its location on the map.")
    return scoped, selected, manifest


def add_markers(figure, layer):
    if layer is None:
        return
    sites, selected, _ = layer
    for kind, color in [("Permanent", "#111111"), ("Mobile Van", "#6A3D9A"),
                        ("Seasonal", "#7A5700")]:
        points = sites.loc[sites.mappable & sites.location_type.eq(kind)]
        if points.empty:
            continue
        text = [f"{escape(str(r['name']))}<br>{escape(str(r['address']))}<br>"
                f"{escape(str(r['city']))}, AZ<br>{kind} · HRSA-listed active site"
                for _, r in points.iterrows()]
        figure.add_trace(go.Scattermap(
            lat=points.latitude, lon=points.longitude, mode="markers", text=text,
            marker={"size": 10, "color": color}, name=f"Health centers · {kind}",
            hovertemplate="%{text}<extra></extra>"))
    chosen = sites.loc[sites.site_id.eq(selected) & sites.mappable]
    if not chosen.empty:
        figure.add_trace(go.Scattermap(
            lat=chosen.latitude, lon=chosen.longitude, mode="markers",
            marker={"size": 18, "color": "#FFDE00"}, name="Selected health center",
            text=[escape(str(chosen.iloc[0]['name']))], hovertemplate="%{text}<extra></extra>"))
        figure.update_layout(map={"center": {"lat": float(chosen.iloc[0].latitude),
                                             "lon": float(chosen.iloc[0].longitude)}, "zoom": 9})


def details(layer):
    if layer is None:
        return
    sites, selected, manifest = layer
    if selected is not None:
        row = sites.loc[sites.site_id.eq(selected)].iloc[0]
        with st.container(border=True):
            st.subheader("Selected health center")
            st.text(f"{row['name']}\n{row['address']}\n{row['city']}, AZ {row['zip']}")
            st.text(f"Phone: {row['phone'] or 'Not supplied'}\n"
                    f"{row['location_type']} · {row['site_type']} · {row['status']}")
            st.caption(f"Coordinate match: {row['geocoding'] or 'Not supplied'}. "
                       "A ZIP-level match is approximate, not a precise facility location.")
            if not row.mappable:
                st.warning("This site has no usable Arizona coordinates; "
                           "it is listed but not mapped.")
    with st.expander("Health-center table and source"):
        st.dataframe(sites[["name", "address", "city", "zip", "county", "phone",
                            "location_type", "status", "geocoding", "mappable"]].rename(columns={
            "name": "Health center", "address": "Address", "city": "City", "zip": "ZIP",
            "county": "County", "phone": "Phone", "location_type": "Location type",
            "status": "HRSA status", "geocoding": "Coordinate match", "mappable": "Mapped"}),
            hide_index=True, width="stretch")
        st.markdown(f"[HRSA source layer]({manifest['source']}) · "
                    "[Find a Health Center](https://findahealthcenter.hrsa.gov/)")
        st.caption("Use this table if you cannot use the map. No distance, catchment area or "
                   "service-gap calculation is performed. "
                   "Facility locations do not enter clustering.")
