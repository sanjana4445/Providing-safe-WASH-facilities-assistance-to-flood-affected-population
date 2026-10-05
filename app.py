import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime

from data_processing import (
    load_5w, build_indicator_summary, build_output_summary, build_palika_summary,
    OUTPUT_COLORS, PALIKAS,
)

st.set_page_config(page_title="Rasuwa WASH Response Dashboard", page_icon="\U0001F4A7", layout="wide")

NAVY = "#0D3B54"
MUTED = "#5B6B78"
BG = "#F6F8FA"

st.markdown(f"""
<style>
.stApp {{ background-color: {BG}; }}
h1, h2, h3 {{ color: {NAVY}; }}
div[data-testid="stMetric"] {{
    background-color: white; border: 1px solid #E2E8F0; border-radius: 10px;
    padding: 14px 16px; box-shadow: 0 1px 2px rgba(0,0,0,0.03);
}}
div[data-testid="stMetricValue"] {{ color: {NAVY}; }}
.block-container {{ padding-top: 1.5rem; }}
</style>
""", unsafe_allow_html=True)

# ----------------------------------------------------------------------
# Data loading (cached; cache clears when the uploaded file content changes)
# ----------------------------------------------------------------------
st.sidebar.title("\U0001F4A7 Rasuwa WASH")
st.sidebar.caption("Chay-Ya \u00d7 UNICEF Nepal \u2014 Rasuwa GLOF Response")

st.sidebar.markdown("### Data source")
uploaded = st.sidebar.file_uploader(
    "Upload the latest 5W export to refresh (optional)", type=["xlsx"],
    help="If you don't upload anything, the dashboard reads the copy bundled in this repo. "
         "To make an update permanent for everyone, replace that file in GitHub instead.",
)
DEFAULT_PATH = "Rasuwa_-_UNICEF_WASH_NEPAL_5Ws_Data_Entry.xlsx"


@st.cache_data(show_spinner="Reading the 5W workbook\u2026")
def get_data(file_bytes_or_path):
    df = load_5w(file_bytes_or_path)
    return df


try:
    source = uploaded if uploaded is not None else DEFAULT_PATH
    df = get_data(source)
except Exception as e:
    st.error(f"Couldn't read the 5W workbook: {e}")
    st.stop()

indicator_summary = build_indicator_summary(df)
output_summary = build_output_summary(indicator_summary)
palika_summary = build_palika_summary(df)

st.sidebar.markdown("---")
st.sidebar.metric("Activity rows loaded", len(df))
unmapped = df[df["output"].isna()]
if len(unmapped):
    st.sidebar.warning(f"{len(unmapped)} row(s) use an Activity this dashboard doesn't yet map to an Output "
                        f"(e.g. 'Other WASH activity - specify'). They're excluded from the totals below.")
st.sidebar.caption(f"Last loaded: {datetime.now().strftime('%d %b %Y, %H:%M')}")

page = st.sidebar.radio("View", ["Overview \u2014 5 Outputs", "Palika-wise breakdown"])

# ========================================================================
# PAGE 1 : OVERVIEW
# ========================================================================
if page == "Overview \u2014 5 Outputs":
    st.title("Providing Safe WASH Facilities & Assistance to Flood-Affected Population")
    st.caption("Progress against the Programme Document's 5 Outputs / 10 indicators, live from the UNICEF 5W tool.")

    tracked = indicator_summary[indicator_summary["tracked_in_5w"]]
    overall_pct = (tracked["progress"].clip(upper=tracked["target"]).sum() / tracked["target"].sum() * 100)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Overall progress (capped at target)", f"{overall_pct:.0f}%")
    c2.metric("Indicators tracked via 5W", f"{int(tracked.shape[0])} / 10")
    c3.metric("Activity rows this period", len(df))
    n_palika_active = (palika_summary["activities"] > 0).sum()
    c4.metric("Palikas with reported activity", f"{n_palika_active} / 4")

    st.markdown("### Output summary")
    cols = st.columns(5)
    for i, row in output_summary.iterrows():
        with cols[i]:
            pct = row["avg_pct"]
            st.markdown(f"<div style='border-left:5px solid {row['color']}; padding:6px 10px; "
                        f"background:white; border-radius:6px; min-height:92px;'>"
                        f"<div style='font-size:12px;color:{MUTED};'>Output {row['output']}</div>"
                        f"<div style='font-size:13px;font-weight:600;color:{NAVY};margin:2px 0 8px 0;'>"
                        f"{row['output_label'].split('\u2013')[1].strip()}</div>"
                        f"<div style='font-size:22px;font-weight:700;color:{row['color']};'>"
                        f"{'n/a' if pd.isna(pct) else f'{pct:.0f}%'}</div></div>", unsafe_allow_html=True)

    st.markdown("### Indicator detail \u2014 target vs. progress")
    for out_num in sorted(indicator_summary["output"].unique()):
        sub = indicator_summary[indicator_summary["output"] == out_num]
        color = OUTPUT_COLORS[out_num]
        st.markdown(f"**{sub['output_label'].iloc[0]}**")
        for _, r in sub.iterrows():
            left, right = st.columns([3, 1])
            with left:
                if r["tracked_in_5w"]:
                    pct = min(r["pct"], 100) if pd.notna(r["pct"]) else 0
                    st.progress(int(pct), text=f"{r['indicator']} \u2014 {r['progress']:,.0f} / {r['target']:,} {r['unit']}"
                                                f" ({r['pct']:.0f}%)" if pd.notna(r['pct']) else r['indicator'])
                else:
                    st.markdown(f"<div style='color:{MUTED};font-size:14px;padding:6px 0;'>"
                                f"{r['indicator']} \u2014 target {r['target']} {r['unit']} "
                                f"<i>(not in 5W \u2014 track via your coordination log)</i></div>", unsafe_allow_html=True)
            with right:
                st.caption(r["unit"])
        st.markdown("")

    st.markdown("### Where the numbers come from")
    fig = go.Figure()
    for _, r in indicator_summary[indicator_summary["tracked_in_5w"]].iterrows():
        fig.add_trace(go.Bar(name=r["indicator"], x=[r["indicator"][:28]], y=[r["progress"]],
                              marker_color=OUTPUT_COLORS[r["output"]], showlegend=False))
        fig.add_trace(go.Scatter(x=[r["indicator"][:28]], y=[r["target"]], mode="markers",
                                  marker=dict(symbol="line-ew", size=28, color=NAVY, line_width=3), showlegend=False))
    fig.update_layout(height=380, plot_bgcolor="white", paper_bgcolor="white",
                       yaxis_title="People / units reached", margin=dict(t=10, b=120))
    st.plotly_chart(fig, width='stretch')
    st.caption("Navy tick = target. Bar = current progress. Two indicators (community feedback mechanisms, "
               "and both Output 1 coordination indicators) aren't in the 5W tool and need manual tracking.")

    with st.expander("How 'People reached' is calculated \u2014 worth reading before you trust these numbers"):
        st.markdown("""
- Each 5W row is matched to one of the 5 Outputs using its **Activity** (and, for schools/CFS/health facilities,
  the **Location Type** overrides the activity-based guess, since Output 4 is about *where* work happens, not what kind).
- For **water, sanitation, and school/CFS activities**, progress is the straight sum of "Total number of beneficiaries reached" across matching rows.
- For **critical WASH supplies and hygiene promotion**, multiple item rows (hygiene kit, bucket, chlorination, different IEC materials)
  often report the *same* households repeatedly \u2014 once per item. Summing those would count the same people several times.
  Instead, this dashboard takes the single largest reported round per Palika for each of these two indicators, not the sum of every item row.
- Rows using an Activity not yet mapped to an Output (shown in the sidebar warning, if any) are excluded from totals \u2014 check the raw sheet.
            """)

# ========================================================================
# PAGE 2 : PALIKA-WISE
# ========================================================================
else:
    st.title("Palika-wise breakdown")
    st.caption("Filter by Palika and Output to see exactly what's been reported where.")

    f1, f2, f3 = st.columns(3)
    sel_palikas = f1.multiselect("Palika", PALIKAS, default=PALIKAS)
    sel_outputs = f2.multiselect("Output", sorted(df["output"].dropna().unique().tolist()),
                                  default=sorted(df["output"].dropna().unique().tolist()),
                                  format_func=lambda o: f"Output {int(o)}")
    sel_status = f3.multiselect("Activity status", sorted(df["status"].dropna().unique().tolist()) or ["Completed", "Ongoing"],
                                 default=sorted(df["status"].dropna().unique().tolist()) or None)

    fdf = df[df["municipality"].isin(sel_palikas) & df["output"].isin(sel_outputs)]
    if sel_status:
        fdf = fdf[fdf["status"].isin(sel_status)]

    st.markdown("### Palika totals")
    psum = palika_summary[palika_summary["palika"].isin(sel_palikas)]
    cols = st.columns(len(psum) if len(psum) else 1)
    for i, (_, r) in enumerate(psum.iterrows()):
        with cols[i]:
            st.metric(r["palika"].replace(" Gaunpalika", ""), f"{r['people_reached']:,.0f} people",
                       f"{r['activities']:.0f} activities \u00b7 {r['households_reached']:,.0f} HH")

    st.markdown("### People reached by Palika and Output")
    chart_df = fdf.copy()
    chart_df["progress"] = chart_df.apply(lambda r: r["people_reached"] if pd.notna(r["people_reached"]) and r["people_reached"] > 0 else 0, axis=1)
    by_out = chart_df.groupby(["municipality", "output"], dropna=True)["progress"].sum().reset_index()
    if len(by_out):
        by_out["Output"] = by_out["output"].map(lambda o: f"Output {int(o)}")
        fig2 = px.bar(by_out, x="municipality", y="progress", color="Output",
                      color_discrete_map={f"Output {k}": v for k, v in OUTPUT_COLORS.items()},
                      labels={"progress": "People reached", "municipality": ""})
        fig2.update_layout(height=380, plot_bgcolor="white", paper_bgcolor="white", legend_title="")
        st.plotly_chart(fig2, width='stretch')
    else:
        st.info("No matching activity for this filter combination.")

    st.markdown("### Demographic reach (selected Palikas)")
    demo = psum[["palika", "girls", "boys", "women", "men", "elderly_women", "elderly_men", "pwd"]].set_index("palika")
    demo.index = demo.index.str.replace(" Gaunpalika", "")
    st.bar_chart(demo, color=["#C77A1E", "#1CABE2", "#159488", "#7C5CBF", "#E1922E", "#64748B", "#A6362C"])
    st.caption("Reflects the same de-duplication logic as the Overview page \u2014 see 'How people reached is calculated.'")

    st.markdown("### Activity log")
    show_cols = ["municipality", "ward", "holding_centre", "type_specific_location", "activity",
                 "activity_description", "modality", "status", "people_reached", "hh_reached", "start_date"]
    st.dataframe(fdf[show_cols].rename(columns={
        "municipality": "Palika", "ward": "Ward", "holding_centre": "Holding Centre",
        "type_specific_location": "Location", "activity": "Activity", "activity_description": "Description",
        "modality": "Modality", "status": "Status", "people_reached": "People reached",
        "hh_reached": "HH reached", "start_date": "Start date",
    }), width='stretch', height=400)
