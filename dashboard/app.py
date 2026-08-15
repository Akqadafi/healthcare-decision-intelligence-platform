"""Executive Streamlit dashboard for community health resource prioritization."""

from __future__ import annotations

import os

import pandas as pd
import plotly.express as px
import streamlit as st

from healthcare_di.config import GOLD_DIR, INTERVENTION_COSTS
from healthcare_di.pipeline import build
from healthcare_di.quality import quality_frame
from healthcare_di.scoring import simulate_allocation

st.set_page_config(
    page_title="Community Health Intelligence",
    page_icon="✦",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
      :root { --ink:#132A2F; --teal:#087E8B; --coral:#F06C5D; --sand:#F5F1E8; }
      .stApp { background: linear-gradient(145deg, #F8FAF8 0%, #EDF5F3 100%); color:var(--ink); }
      [data-testid="stSidebar"] { background:#102F35; }
      [data-testid="stSidebar"] * { color:#F7FAF9 !important; }
      .hero { padding:1.4rem 1.6rem; border-radius:18px; color:white;
              background:linear-gradient(115deg,#123E46,#087E8B 68%,#31A6A0); margin-bottom:1rem; }
      .hero .eyebrow { letter-spacing:.16em; text-transform:uppercase;
                       font-size:.72rem; opacity:.78; }
      .hero h1 { font-size:2.25rem; margin:.25rem 0; line-height:1.08; }
      .hero p { max-width:760px; margin:.3rem 0 0; color:#E5F5F3; }
      .callout { border-left:4px solid #F06C5D; background:white; border-radius:8px;
                 padding:.9rem 1rem; box-shadow:0 7px 24px rgba(19,42,47,.07); }
      [data-testid="stMetric"] { background:white; border:1px solid #DBE8E5;
                                padding:.85rem 1rem; border-radius:12px; }
      div[data-baseweb="tab-list"] { gap:1rem; }
      .small-note { color:#52676B; font-size:.82rem; }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(show_spinner=False)
def load_data(live: bool = False) -> pd.DataFrame:
    path = GOLD_DIR / "mart_community_priority.csv"
    if live or not path.exists():
        return build(live=live)
    return pd.read_csv(path, dtype={"county_fips": str})


live_requested = os.getenv("HDIP_LIVE_DATA", "0") == "1"
try:
    mart = load_data(live_requested)
except Exception as exc:
    st.error(f"The data pipeline could not start: {exc}")
    st.stop()

with st.sidebar:
    st.markdown("## Decision controls")
    tiers = st.multiselect(
        "Priority tier",
        options=["Critical", "High", "Elevated", "Monitor"],
        default=["Critical", "High", "Elevated", "Monitor"],
    )
    minimum_population = st.number_input(
        "Minimum population", min_value=0, max_value=5_000_000, value=0, step=10_000
    )
    st.markdown("---")
    st.markdown("**Data mode**  ")
    data_mode = "Bundled, reproducible public-data snapshot"
    st.caption(data_mode if not live_requested else "Live API refresh")
    st.caption("No patient-level or protected health information is used.")

filtered = mart[
    mart["priority_tier"].isin(tiers) & (mart["population"] >= minimum_population)
].copy()

st.markdown(
    """
    <section class="hero">
      <div class="eyebrow">Healthcare access · risk · resource allocation</div>
      <h1>Community Health Operations Intelligence</h1>
      <p>Turn public population-health and hospital data into transparent, action-ready
      investment priorities for Arizona communities.</p>
    </section>
    """,
    unsafe_allow_html=True,
)

if filtered.empty:
    st.warning("No counties match the current filters.")
    st.stop()

leader = filtered.iloc[0]
metric_cols = st.columns(4)
metric_cols[0].metric("Counties in view", f"{len(filtered)}")
metric_cols[1].metric("Highest-priority county", leader["county_name"])
metric_cols[2].metric("Top priority score", f"{leader['total_priority_score']:.1f} / 100")
metric_cols[3].metric("Population represented", f"{filtered['population'].sum():,.0f}")

tabs = st.tabs(["Executive summary", "Map & county profile", "Resource simulator", "Trust center"])

with tabs[0]:
    left, right = st.columns([1.35, 1])
    with left:
        st.subheader("Where to invest first")
        ranking = filtered.sort_values("rank").head(10)
        fig = px.bar(
            ranking.sort_values("total_priority_score"),
            x="total_priority_score",
            y="county_name",
            orientation="h",
            color="priority_tier",
            color_discrete_map={
                "Critical": "#B33A3A",
                "High": "#F06C5D",
                "Elevated": "#F2B95F",
                "Monitor": "#74A89F",
            },
            labels={"total_priority_score": "Priority score", "county_name": ""},
        )
        fig.update_layout(height=430, legend_title_text="", margin=dict(l=0, r=10, t=10, b=0))
        st.plotly_chart(fig, width="stretch")
    with right:
        st.subheader("Recommended first move")
        st.markdown(
            f"""
            <div class="callout">
              <strong>{leader['county_name']} County · {leader['priority_tier']}</strong><br>
              <span style="font-size:1.08rem">{leader['recommended_action']}</span><br><br>
              <span class="small-note">Why: {leader['primary_drivers']}. This is a planning
              recommendation, not a causal claim or clinical decision.</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown("#### Domain scores")
        domains = pd.DataFrame(
            {
                "Domain": ["Health burden", "Social need", "Care access", "Hospital gap"],
                "Score": [
                    leader["health_burden_score"],
                    leader["sdoh_score"],
                    leader["access_score"],
                    leader["hospital_gap_score"],
                ],
            }
        )
        domain_fig = px.bar(
            domains,
            x="Score",
            y="Domain",
            orientation="h",
            range_x=[0, 100],
            color="Score",
            color_continuous_scale=[[0, "#CDE5DF"], [1, "#F06C5D"]],
        )
        domain_fig.update_layout(
            height=280, coloraxis_showscale=False, margin=dict(l=0, r=0, t=5, b=0)
        )
        st.plotly_chart(domain_fig, width="stretch")

    st.dataframe(
        ranking[
            [
                "rank",
                "county_name",
                "priority_tier",
                "total_priority_score",
                "primary_drivers",
                "recommended_action",
            ]
        ],
        hide_index=True,
        width="stretch",
        column_config={"total_priority_score": st.column_config.ProgressColumn(max_value=100)},
    )

with tabs[1]:
    map_fig = px.scatter_map(
        filtered,
        lat="latitude",
        lon="longitude",
        size="population",
        size_max=34,
        color="total_priority_score",
        hover_name="county_name",
        hover_data={
            "priority_tier": True,
            "recommended_action": True,
            "latitude": False,
            "longitude": False,
            "population": ":,",
        },
        color_continuous_scale=[[0, "#7BC8BC"], [0.55, "#F2B95F"], [1, "#B33A3A"]],
        range_color=[0, 100],
        zoom=4.5,
        center={"lat": 34.2, "lon": -111.8},
        map_style="carto-positron",
    )
    map_fig.update_layout(height=500, margin=dict(l=0, r=0, t=0, b=0))
    st.plotly_chart(map_fig, width="stretch")

    county = st.selectbox("County profile", filtered.sort_values("rank")["county_name"])
    row = filtered.loc[filtered["county_name"].eq(county)].iloc[0]
    profile_cols = st.columns(6)
    profile_cols[0].metric("Priority", f"#{row['rank']}")
    profile_cols[1].metric("Uninsured", f"{row['uninsured_rate']:.1f}%")
    profile_cols[2].metric("Poverty", f"{row['poverty_rate']:.1f}%")
    profile_cols[3].metric("Median income", f"${row['median_household_income']:,.0f}")
    profile_cols[4].metric("Hospitals", f"{row['hospital_count']:.0f}")
    rating = (
        "Not enough data"
        if pd.isna(row["average_hospital_rating"])
        else f"{row['average_hospital_rating']:.1f} / 5"
    )
    profile_cols[5].metric("Avg. CMS rating", rating)
    st.info(
        f"**Recommended action:** {row['recommended_action']}  \n\n"
        f"**Primary drivers:** {row['primary_drivers']}"
    )

with tabs[2]:
    st.subheader("Resource allocation scenario")
    control_a, control_b, control_c = st.columns(3)
    budget = control_a.slider("Available budget", 25_000, 1_000_000, 250_000, 25_000)
    intervention = control_b.selectbox("Intervention", list(INTERVENTION_COSTS))
    max_communities = control_c.slider("Operational capacity (counties)", 1, 15, 5)
    allocation = simulate_allocation(filtered, budget, intervention, max_communities)
    spent = int(allocation["allocated_budget"].sum()) if not allocation.empty else 0
    reached = int(allocation["estimated_people_reached"].sum()) if not allocation.empty else 0
    a, b, c = st.columns(3)
    a.metric("Recommended counties", len(allocation))
    b.metric("Allocated", f"${spent:,.0f}", f"${budget-spent:,.0f} unallocated")
    c.metric("Planning reach estimate", f"{reached:,}")
    st.dataframe(
        allocation,
        hide_index=True,
        width="stretch",
        column_config={
            "allocated_budget": st.column_config.NumberColumn(format="$%d"),
            "total_priority_score": st.column_config.ProgressColumn(max_value=100),
        },
    )
    st.caption(
        "Planning reach is a transparent heuristic (2% of county population, bounded at 250-5,000) "
        "and must be replaced with program-specific capacity assumptions before operational use."
    )

with tabs[3]:
    st.subheader("Data quality and governance")
    checks = quality_frame(mart)
    passed = int(checks["passed"].sum())
    q1, q2, q3 = st.columns(3)
    q1.metric("Automated checks", len(checks))
    q2.metric("Checks passed", f"{passed} / {len(checks)}")
    q3.metric("PHI records", "0")
    st.dataframe(checks, hide_index=True, width="stretch")
    st.markdown(
        """
        **Lineage:** CDC PLACES + CMS Hospital General Information → normalized county keys →
        four explainable domain scores → weighted priority mart → dashboard and simulator.

        **Limitations:** PLACES estimates are modeled and should not be used to evaluate local
        program effects. CMS missing ratings represent insufficient data, not poor performance.
        Scores support planning; they do not replace local validation, community input, or
        clinical judgment.
        """
    )

st.caption(
    "Public aggregate data only · CDC PLACES 2025 · Census ACS 2024 5-year · "
    "CMS modified April 2026"
)
