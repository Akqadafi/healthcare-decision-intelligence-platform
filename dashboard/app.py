"""Executive Streamlit dashboard for community health resource prioritization."""

from __future__ import annotations

import base64
import os
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from healthcare_di.config import GOLD_DIR, INTERVENTION_COSTS
from healthcare_di.pipeline import build
from healthcare_di.quality import quality_frame
from healthcare_di.scoring import (
    DOMAIN_WEIGHTS,
    explain_priority_mart,
    rating_sensitivity,
    simulate_allocation,
)

st.set_page_config(
    page_title="Community Health Intelligence",
    page_icon="🌵",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
      :root { --ink:#302D25; --rust:#9F492E; --sage:#68765A; --sand:#F6F0E4; }
      .stApp { background:linear-gradient(145deg,#FBF7EF 0%,#F1E6D2 100%); color:var(--ink); }
      [data-testid="stHeader"] { background:rgba(251,247,239,.95); }
      [data-testid="stSidebar"] { background:#E5E7D8; border-right:1px solid #CFD4BE; }
      .hero { position:relative; overflow:hidden; padding:1.6rem 1.8rem;
              border-radius:18px; color:#FFF8EC; margin-bottom:1.3rem;
              background:linear-gradient(115deg,#613928 0%,#8B462F 60%,#B86D3E 100%);
              border:1px solid #A6603D; box-shadow:0 12px 32px rgba(90,54,35,.12); }
      .hero > :not(.desert-scene) { position:relative; z-index:1; }
      .hero .eyebrow { letter-spacing:.13em; text-transform:uppercase;
                       font-size:.72rem; color:#F1D6AC; margin-top:1.2rem; }
      .hero h1 { font-size:2.2rem; margin:.4rem 0; line-height:1.12; max-width:850px; }
      .hero p { max-width:760px; margin:.7rem 0 0; color:#FFF3E1; }
      [data-testid="stMainBlockContainer"] { padding-bottom:1rem; }
      .dashboard-footer { display:flex; align-items:center; justify-content:space-between;
                          gap:.75rem; flex-wrap:nowrap; margin-top:.75rem; padding:0;
                          background:transparent; border:0; }
      .footer-logo { position:relative; display:block; flex:0 0 200px; width:200px;
                     aspect-ratio:1200 / 546; overflow:hidden; }
      .footer-logo img { position:absolute; display:block; width:147.834%; max-width:none;
                         height:auto; left:-24%; top:-37.363%; }
      .footer-name { color:#613928; font-size:1.15rem; font-weight:700; }
      .footer-name small { display:block; margin-top:.3rem; font-size:.8rem;
                           color:#68765A; font-weight:400; }
      .desert-scene { position:absolute; right:0; bottom:0; width:46%; height:100%;
                      opacity:.24; pointer-events:none; }
      .callout { border-left:4px solid #B7663F; background:#FFFBF4; border-radius:8px;
                 padding:.9rem 1rem; box-shadow:0 7px 24px rgba(90,54,35,.07); }
      [data-testid="stMetric"] { background:#FFFBF4; border:1px solid #DECFB5;
                                padding:.85rem 1rem; border-radius:12px; }
      div[data-baseweb="tab-list"] { gap:1rem; }
      .small-note { color:#66584A; font-size:.82rem; }
      @media (max-width:1100px) {
        [data-testid="stHorizontalBlock"]:has([data-testid="stMetric"]) {
          display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); }
        [data-testid="stHorizontalBlock"]:has([data-testid="stPlotlyChart"]) {
          flex-direction:column; }
        [data-testid="stHorizontalBlock"]:has([data-testid="stMetric"]) >
        [data-testid="stColumn"],
        [data-testid="stHorizontalBlock"]:has([data-testid="stPlotlyChart"]) >
        [data-testid="stColumn"] { width:100% !important; min-width:0; }
        [data-testid="stMetricValue"] { font-size:1.65rem; }
      }
      @media (max-width:640px) {
        [data-testid="stHorizontalBlock"]:has([data-testid="stMetric"]) {
          grid-template-columns:1fr; }
        .hero { padding:1.2rem; }
        .hero h1 { font-size:1.7rem; }
        .desert-scene { width:75%; opacity:.15; }
        .footer-logo { flex-basis:140px; width:140px; }
        .footer-name { font-size:1rem; }
        .footer-name small { font-size:.7rem; }
      }
    </style>
    """,
    unsafe_allow_html=True,
)


def render_footer() -> None:
    """Show the user's selected logo and attribution after each page's content."""
    logo = Path(__file__).parent / "assets" / "aq-systems-desert.png"
    encoded = base64.b64encode(logo.read_bytes()).decode("ascii")
    st.markdown(
        f'<footer class="dashboard-footer">'
        '<div class="footer-name">Ahmad Qadafi'
        '<small>Cloud Engineering &middot; Data Systems</small></div>'
        '<span class="footer-logo">'
        f'<img src="data:image/png;base64,{encoded}" alt="AQ Systems logo"></span></footer>',
        unsafe_allow_html=True,
    )
    st.caption(
        "Public aggregate data only · CDC PLACES 2025 · Census ACS 2024 5-year · "
        "CMS modified April 2026"
    )


@st.cache_data(show_spinner=False)
def load_data(live: bool = False) -> pd.DataFrame:
    path = GOLD_DIR / "mart_community_priority.csv"
    if live or not path.exists():
        return build(live=live)
    return pd.read_csv(path, dtype={"county_fips": str})


live_requested = os.getenv("HDIP_LIVE_DATA", "0") == "1"
try:
    mart = explain_priority_mart(load_data(live_requested))
except Exception as exc:
    st.error(f"The data pipeline could not start: {exc}")
    render_footer()
    st.stop()

with st.sidebar:
    page = st.radio(
        "Dashboard index", ["Start here", "Explore counties", "Metrics & methods", "Trust center"]
    )
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
      <svg class="desert-scene" viewBox="0 0 500 300" preserveAspectRatio="xMaxYMax slice"
           aria-hidden="true" focusable="false">
        <circle cx="385" cy="82" r="45" fill="#F3C575"/>
        <path d="M0 250L95 155L142 197L205 117L280 195L339 153L430 222L500 180V300H0Z"
              fill="#D8A06B"/>
        <path d="M0 274L84 228L150 249L238 208L324 252L414 210L500 256V300H0Z"
              fill="#482F28"/>
        <path d="M430 290V163M430 223H408Q399 223 399 210V190M430 204H450Q460 204 460 191V178"
              fill="none" stroke="#24372D" stroke-width="15" stroke-linecap="round"/>
      </svg>
      <h1>Community Health Operations Intelligence</h1>
      <p>Turning public population health and hospital data into transparent, action-ready
      planning priorities for Arizona communities</p>
    </section>
    """,
    unsafe_allow_html=True,
)

if page == "Start here":
    st.subheader("What this dashboard looks at")
    st.write(
        "This portfolio dashboard compares public health, social need, care access, and "
        "hospital-rating measures across all 15 Arizona counties. It creates a relative "
        "priority score to help a planner decide which counties deserve closer review."
    )
    st.markdown("""
    **The planning question:** Where might outreach and healthcare resources
    warrant further investigation?

    **How it works:** CDC PLACES, Census ACS, and CMS hospital records are joined by county.
    Most measures become percentile scores relative to the 15 counties. Four domains are
    weighted into a 0–100 priority score. Ordered rules suggest an action, and a budget
    scenario demonstrates allocating one assumed intervention unit per selected county.

    **What the results mean:** A higher score means higher relative priority under this
    model's assumptions. It is not a probability, a count of people needing care, or evidence
    that an intervention will work. County averages can hide differences within communities.

    **Reading guide**
    1. **Explore counties:** Compare rankings, inspect a county, and try an allocation scenario.
    2. **Metrics & methods:** Read metric definitions, weights, action rules,
       and missing-data assumptions.
    3. **Trust center:** Review checks and compare rankings under alternative rating assumptions.

    **Before operational use:** Review source definitions and dates, validate local needs with
    community partners, agree on weights and thresholds, and replace assumed costs and reach
    with program-specific evidence. This is a deterministic planning model, not an AI prediction.
    """)
    st.info(
        "Public aggregate data only. Bundled snapshots: CDC PLACES 2025, Census ACS 2024 "
        "5-year, CMS modified April 2026. These labels describe source releases, "
        "not a shared observation year."
    )
    render_footer()
    st.stop()

if page == "Metrics & methods":
    st.subheader("Metrics glossary and scoring methods")
    st.markdown(
        "**Score formula:** Health burden × 35% + Social need × 25% + Care access × 25% "
        "+ Hospital gap × 15%. Weights and action thresholds are project assumptions."
    )
    st.write(
        "For percentile-based inputs, 0 is the lowest relative need and 100 the highest "
        "among all 15 counties; ties receive average ranks. Sidebar filters do not recompute "
        "scores or statewide ranks. Missing numeric percentile inputs use the statewide median."
    )
    st.dataframe(
        pd.DataFrame(
            [
                [
                    "Obesity / diabetes / hypertension",
                    "CDC PLACES crude prevalence (%)",
                    "Higher = more need",
                    "Health: 25% / 25% / 20%",
                ],
                [
                    "Poor physical / mental health",
                    "CDC PLACES frequent distress measures (%)",
                    "Higher = more need",
                    "Health: 15% each",
                ],
                [
                    "Food insecurity",
                    "CDC PLACES food insecurity measure (%)",
                    "Higher = more need",
                    "Social: 30%",
                ],
                [
                    "Uninsured",
                    "CDC PLACES lack of insurance measure (%)",
                    "Higher = more need",
                    "Social: 25%",
                ],
                [
                    "Poverty",
                    "Census ACS percent below poverty level",
                    "Higher = more need",
                    "Social: 30%",
                ],
                [
                    "Median household income",
                    "Census ACS household income (dollars)",
                    "Lower = more need",
                    "Social: 15%",
                ],
                [
                    "Transportation barriers",
                    "CDC PLACES lack of reliable transportation (%)",
                    "Higher = more need",
                    "Access: 40%",
                ],
                [
                    "Annual checkup",
                    "CDC PLACES routine checkup measure (%)",
                    "Lower = more need",
                    "Access: 25%",
                ],
                [
                    "Hospitals per 100,000",
                    "CMS facility count / county population × 100,000",
                    "Lower = more need",
                    "Access: 35%",
                ],
                [
                    "Average CMS rating",
                    "Mean of available hospital overall ratings (1–5); unrated excluded",
                    "Gap = (5 − rating) / 4 × 100",
                    "Hospital: 100%",
                ],
                [
                    "Population / FIPS",
                    "County population denominator / five-digit county identifier",
                    "Context and joins",
                    "No direct weight",
                ],
                [
                    "Primary drivers",
                    "Two largest weighted contributions to the total",
                    "Contribution = domain × weight",
                    "Not the action trigger",
                ],
            ],
            columns=[
                "Metric",
                "Definition in this model",
                "Direction / calculation",
                "Within-domain weight",
            ],
        ),
        hide_index=True,
        width="stretch",
    )
    st.caption(
        "PLACES percentages have measure-specific eligible populations; they are not all "
        "percentages of total county population. See source documentation for full definitions."
    )
    st.markdown(
        "[CDC PLACES definitions]"
        "(https://www.cdc.gov/places/measure-definitions/index.html) · "
        "[Census ACS](https://www.census.gov/programs-surveys/acs) · "
        "[CMS hospital data](https://data.cms.gov/provider-data/topics/hospitals)"
    )
    st.markdown("""
    **Priority tiers:** Monitor ≤40; Elevated >40–60; High >60–75; Critical >75.
    Scores are rounded to one decimal before tiers and ranks. Tied totals use source county order.

    **Missing hospital ratings:** The baseline substitutes a hospital-gap score of **60**, adding
    **9 points** to the total. This assumption does not establish poor hospital performance.
    The Trust center compares it with 50 (7.5 points) and excluding the domain while renormalizing
    remaining weights to sum to 100%. Missing hospital counts are filled with zero.

    **Suggested-action rules, evaluated in order:**
    1. Highest unweighted domain is care access **or** transportation barriers ≥12%:
       mobile clinic and transportation outreach.
    2. Highest unweighted domain is social need **and** uninsured ≥18%: benefits navigation.
    3. Poor mental health ≥18%: behavioral health outreach.
    4. Highest unweighted domain is hospital gap: hospital quality and referral partnership.
    5. Otherwise: chronic disease prevention and care coordination.

    The first matching rule wins. These are planning hypotheses, not validated clinical thresholds.
    Unweighted domain ties use health, social, access, then hospital order.
    """)
    render_footer()
    st.stop()

if page == "Trust center":
    st.subheader("Data checks and modeling assumptions")
    checks = quality_frame(mart)
    q1, q2 = st.columns(2)
    q1.metric("Structural checks", len(checks))
    q2.metric("Checks passed", f"{int(checks['passed'].sum())} / {len(checks)}")
    st.info(
        "Public aggregate data only. This describes the input design; "
        "no automated PHI scan is performed."
    )
    st.dataframe(checks, hide_index=True, width="stretch")
    st.write(
        "These checks cover required columns, 15 county rows, unique identifiers, FIPS format, "
        "score bounds, and non-null actions. They run on the full dataset. They do not validate "
        "the chosen weights, source accuracy, intervention effectiveness, or privacy compliance."
    )
    st.markdown(
        "**Lineage:** CDC PLACES + Census ACS + CMS hospital data → normalized county keys "
        "→ four domain scores → weighted priority mart → dashboard and allocation scenario."
    )
    st.subheader("Do rankings change when missing ratings are treated differently?")
    st.caption(
        "All counties are compared with other inputs fixed. Alternatives affect only counties "
        "without ratings. The baseline dashboard remains unchanged; these are sensitivity "
        "comparisons, not recalculated action recommendations."
    )
    comparison = rating_sensitivity(mart)
    changed_50 = int((comparison["Baseline rank"] != comparison["Missing = 50: rank"]).sum())
    changed_excluded = int(
        (comparison["Baseline rank"] != comparison["Exclude missing domain: rank"]).sum()
    )
    st.write(
        f"Rank changes: **{changed_50} counties** with missing = 50; "
        f"**{changed_excluded} counties** when the missing domain is excluded."
    )
    st.dataframe(comparison, hide_index=True, width="stretch")
    st.warning(
        "PLACES estimates are modeled. County associations do not establish causes or program "
        "effects. Review uncertainty, local conditions, community input, and scoring assumptions "
        "before making funding decisions."
    )
    render_footer()
    st.stop()

if filtered.empty:
    st.warning("No counties match the current filters.")
    render_footer()
    st.stop()

leader = filtered.iloc[0]
metric_cols = st.columns(4)
metric_cols[0].metric("Counties in view", f"{len(filtered)}")
metric_cols[1].metric("Highest-priority county", leader["county_name"])
metric_cols[2].metric("Top priority score", f"{leader['total_priority_score']:.1f} / 100")
metric_cols[3].metric("Population represented", f"{filtered['population'].sum():,.0f}")

tabs = st.tabs(["Executive summary", "Map & county profile", "Allocation scenario"])

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
                "Critical": "#8B392D",
                "High": "#B8673F",
                "Elevated": "#C69745",
                "Monitor": "#748266",
            },
            labels={"total_priority_score": "Priority score", "county_name": ""},
        )
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            height=430,
            legend_title_text="",
            margin=dict(l=0, r=10, t=10, b=0),
        )
        st.plotly_chart(fig, width="stretch")
    with right:
        st.subheader("Recommended first move")
        st.markdown(
            f"""
            <div class="callout">
              <strong>{leader["county_name"]} County · {leader["priority_tier"]}</strong><br>
              <span style="font-size:1.08rem">{leader["recommended_action"]}</span><br><br>
              <span class="small-note">Action rule: {leader["action_reason"]} This is a planning
              recommendation, not a causal claim or clinical decision.</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown("#### What contributes to the total?")
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
            color_continuous_scale=[[0, "#D9DFC5"], [1, "#B8673F"]],
        )
        domain_fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            height=280,
            coloraxis_showscale=False,
            margin=dict(l=0, r=0, t=5, b=0),
        )
        st.plotly_chart(domain_fig, width="stretch")
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "Domain": label,
                        "Points in total": round(leader[column] * weight, 1),
                        "Weight": f"{weight:.0%}",
                        "Domain score": round(leader[column], 1),
                    }
                    for column, (label, weight) in DOMAIN_WEIGHTS.items()
                ]
            ),
            hide_index=True,
            width="stretch",
        )
        st.caption(
            "Bars show unweighted scores; table shows weighted contributions. "
            "Primary drivers are the two largest contributions. Rounding can affect displayed sums."
        )

    st.caption(
        "Showing the ten highest-ranked counties in the current view. "
        "Statewide scores and ranks remain fixed when filters change."
    )
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
        color_continuous_scale=[[0, "#8C9D76"], [0.55, "#C69745"], [1, "#8B392D"]],
        range_color=[0, 100],
        zoom=4.5,
        center={"lat": 34.2, "lon": -111.8},
        map_style="carto-positron",
    )
    map_fig.update_layout(height=500, margin=dict(l=0, r=0, t=0, b=0))
    st.plotly_chart(map_fig, width="stretch")

    county = st.selectbox("County profile", filtered.sort_values("rank")["county_name"])
    row = filtered.loc[filtered["county_name"].eq(county)].iloc[0]
    profile_cols = st.columns(3)
    profile_cols[0].metric("Priority", f"#{row['rank']}")
    profile_cols[1].metric("Uninsured", f"{row['uninsured_rate']:.1f}%")
    profile_cols[2].metric("Poverty", f"{row['poverty_rate']:.1f}%")
    profile_cols = st.columns(3)
    profile_cols[0].metric("Median income", f"${row['median_household_income']:,.0f}")
    profile_cols[1].metric("Hospitals", f"{row['hospital_count']:.0f}")
    rating = (
        "Not enough data"
        if pd.isna(row["average_hospital_rating"])
        else f"{row['average_hospital_rating']:.1f} / 5"
    )
    profile_cols[2].metric("Avg. CMS rating", rating)
    st.info(
        f"**Recommended action:** {row['recommended_action']}  \n\n"
        f"**Action rule:** {row['action_reason']}  \n\n"
        f"**Largest weighted contributions:** {row['primary_drivers']}"
    )

    st.markdown("#### County score contributions")
    st.dataframe(
        pd.DataFrame(
            [
                {
                    "Domain": label,
                    "Points in total": round(row[column] * weight, 1),
                    "Weight": f"{weight:.0%}",
                    "Domain score": round(row[column], 1),
                }
                for column, (label, weight) in DOMAIN_WEIGHTS.items()
            ]
        ),
        hide_index=True,
        width="stretch",
    )
    if pd.isna(row["average_hospital_rating"]):
        st.caption(
            "No hospital rating is available. The assumed hospital-gap score of 60 "
            "adds 9 points. Compare alternative assumptions in the Trust center."
        )

with tabs[2]:
    st.subheader("Resource allocation scenario")
    st.info(
        "This scenario demonstrates allocation mechanics. Costs are fixed project assumptions; "
        "reach is a generic population heuristic, not intervention capacity or predicted outcomes."
    )
    st.markdown(
        "**How to use this page**\n"
        "1. Use the sidebar filters to choose which counties to consider.\n"
        "2. Set your **available budget**, choose an **intervention**, and set the maximum "
        "number of counties your team can support.\n"
        "3. Review the selected counties and allocated budget below. The scenario funds one "
        "intervention unit per county, starting with the highest priority score, until the "
        "budget or county limit is reached.\n"
        "4. Change a control to compare scenarios. **Unallocated** is the budget left over; "
        "**illustrative reach** is a population-based assumption, not a forecast of people served."
    )
    control_a, control_b, control_c = st.columns(3)
    budget = control_a.slider("Available budget", 25_000, 1_000_000, 250_000, 25_000)
    intervention = control_b.selectbox("Intervention", list(INTERVENTION_COSTS))
    max_communities = control_c.slider("Operational capacity (counties)", 1, 15, 5)
    allocation = simulate_allocation(filtered, budget, intervention, max_communities)
    spent = int(allocation["allocated_budget"].sum()) if not allocation.empty else 0
    reached = int(allocation["estimated_people_reached"].sum()) if not allocation.empty else 0
    a, b, c = st.columns(3)
    a.metric("Recommended counties", len(allocation))
    b.metric("Allocated", f"${spent:,.0f}", f"${budget - spent:,.0f} unallocated")
    c.metric("Illustrative reach", f"{reached:,}")
    st.dataframe(
        allocation.rename(columns={"estimated_people_reached": "illustrative_reach"}),
        hide_index=True,
        width="stretch",
        column_config={
            "allocated_budget": st.column_config.NumberColumn(format="$%d"),
            "total_priority_score": st.column_config.ProgressColumn(max_value=100),
        },
    )
    st.markdown(
        f"**Assumed unit cost:** ${INTERVENTION_COSTS[intervention]:,}. "
        "One unit per county, selected by descending score, up to the budget, county count, "
        "and capacity limit. Remaining budget is left unallocated."
    )
    with st.expander("All assumed intervention costs"):
        st.dataframe(
            pd.DataFrame(INTERVENTION_COSTS.items(), columns=["Intervention", "Assumed cost ($)"]),
            hide_index=True,
            width="stretch",
        )
    st.caption(
        "Planning reach is a transparent heuristic (2% of county population, bounded at 250-5,000) "
        "using the same formula for every intervention. It does not estimate unique people served "
        "or health outcomes. Replace it with program-specific capacity before operational use."
    )


render_footer()
