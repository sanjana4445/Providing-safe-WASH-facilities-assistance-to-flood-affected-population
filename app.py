import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime

from data_processing import (
    load_5w, build_indicator_summary, build_output_summary, build_palika_summary,
    build_palika_output_summary, build_monitoring_workbook, OUTPUT_COLORS, PALIKAS,
)

st.set_page_config(page_title="Rasuwa WASH Response Dashboard", page_icon="\U0001F4A7", layout="wide")

NAVY = "#123B4A"
MUTED = "#5B6B70"
BG = "#F2F6F5"
PARTNER_ALIASES = {
    "unicef": "UNICEF", "unicef nepal": "UNICEF",
    "chay ya": "Chay-Ya Nepal", "chay ya nepal": "Chay-Ya Nepal",
}
PARTNER_SCOPE = ["Chay-Ya Nepal", "UNICEF"]
MAP_ID = "1qtThPTqZuAuCMHl_Oqkq-0OW-ZFdjsU"
MAP_EMBED_URL = f"https://www.google.com/maps/d/embed?mid={MAP_ID}"
MAP_EDIT_URL = f"https://www.google.com/maps/d/u/0/edit?mid={MAP_ID}"

st.markdown(f"""
<style>
.stApp {{ background-color: {BG}; color: #203238; }}
h1, h2, h3 {{ color: {NAVY}; letter-spacing: 0; }}
div[data-testid="stMetric"] {{
    background-color: white; border: 1px solid #DFE8E5; border-top: 3px solid #159488;
    border-radius: 7px; padding: 14px 16px; box-shadow: 0 2px 8px rgba(18,59,74,0.04);
}}
div[data-testid="stMetricValue"] {{ color: {NAVY}; }}
.block-container {{ padding-top: 1.35rem; padding-bottom: 2.5rem; }}
div[data-testid="stSidebar"] {{ background-color: #E8F0ED; }}
div[data-testid="stProgress"] > div > div {{ background-color: #159488; }}
</style>
""", unsafe_allow_html=True)

st.sidebar.title("\U0001F4A7 Rasuwa WASH")
st.sidebar.caption("Chay-Ya Nepal \u00d7 UNICEF Nepal \u2014 Rasuwa GLOF Response")
st.sidebar.markdown("### Data source")
uploaded = st.sidebar.file_uploader(
    "Upload the latest 5W export to refresh (optional)", type=["xlsx"],
    help="If you don't upload anything, the dashboard reads the copy bundled in this repo. "
         "To make an update permanent for everyone, replace that file in GitHub instead.",
)
DEFAULT_PATH = "Rasuwa_-_UNICEF_WASH_NEPAL_5Ws_Data_Entry.xlsx"


@st.cache_data(show_spinner="Reading the 5W workbook\u2026")
def get_data(file_bytes_or_path):
    return load_5w(file_bytes_or_path)


try:
    source = uploaded if uploaded is not None else DEFAULT_PATH
    df = get_data(source)
except Exception as exc:
    st.error(f"Couldn't read the 5W workbook: {exc}")
    st.stop()

normalized_partners = (
    df["partner"].astype("string").str.casefold()
    .str.replace(r"[^a-z0-9]+", " ", regex=True).str.strip()
)
df["partner"] = normalized_partners.map(PARTNER_ALIASES)
excluded_partner_rows = int(df["partner"].isna().sum())
df = df[df["partner"].notna()].copy()

indicator_summary = build_indicator_summary(df)
output_summary = build_output_summary(indicator_summary)
palika_summary = build_palika_summary(df)
unmapped = df[df["output"].isna()]

st.sidebar.markdown("---")
st.sidebar.metric("Activity rows loaded", len(df))
st.sidebar.caption("Reporting scope: Chay-Ya Nepal and UNICEF only")
if excluded_partner_rows:
    st.sidebar.caption(f"{excluded_partner_rows} record(s) outside this scope excluded.")
if len(unmapped):
    st.sidebar.warning(
        f"{len(unmapped)} row(s) use an Activity this dashboard doesn't yet map to an Output "
        "and are excluded from totals. Review them in the Excel export."
    )
st.sidebar.caption(f"Last loaded: {datetime.now().strftime('%d %b %Y, %H:%M')}")
st.sidebar.download_button(
    "Download Excel monitoring pack",
    data=build_monitoring_workbook(df),
    file_name=f"rasuwa_wash_5w_monitoring_{datetime.now():%Y%m%d}.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    use_container_width=True,
    help="Includes indicator and Palika trackers, the full 5W register, and data-quality checks.",
)

page = st.sidebar.radio("View", ["Programme overview", "Activity monitoring", "Project site map"])

if page == "Programme overview":
    st.title("Providing Safe WASH Facilities & Assistance to Flood-Affected Population")
    st.caption("Progress against the Programme Document's 5 Outputs / 10 indicators, live from the UNICEF 5W tool.")

    tracked = indicator_summary[indicator_summary["tracked_in_5w"]]
    denominator = tracked["target"].sum()
    overall_pct = tracked["progress"].clip(upper=tracked["target"]).sum() / denominator * 100 if denominator else 0
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Overall progress (capped at target)", f"{overall_pct:.0f}%")
    c2.metric("Indicators tracked via 5W", f"{int(tracked.shape[0])} / 10")
    c3.metric("Activity records", f"{len(df):,}")
    active_palikas = (palika_summary["activities"] > 0).sum()
    c4.metric("Palikas with reported activity", f"{active_palikas} / 4")

    st.markdown("### Output summary")
    output_columns = st.columns(5)
    for index, row in output_summary.iterrows():
        with output_columns[index]:
            percent = row["avg_pct"]
            label = row["output_label"].split("\u2013", 1)[-1].strip()
            value = "n/a" if pd.isna(percent) else f"{percent:.0f}%"
            st.markdown(
                f"<div style='border-left:5px solid {row['color']}; padding:8px 11px; "
                f"background:white; border-radius:5px; min-height:96px;'>"
                f"<div style='font-size:12px;color:{MUTED};'>Output {row['output']}</div>"
                f"<div style='font-size:13px;font-weight:600;color:{NAVY};margin:3px 0 8px 0;'>"
                f"{label}</div><div style='font-size:22px;font-weight:700;color:{row['color']};'>"
                f"{value}</div></div>",
                unsafe_allow_html=True,
            )

    st.markdown("### Indicator detail | target vs. progress")
    for output_number in sorted(indicator_summary["output"].unique()):
        subset = indicator_summary[indicator_summary["output"] == output_number]
        st.markdown(f"**{subset['output_label'].iloc[0]}**")
        for _, row in subset.iterrows():
            left, right = st.columns([3, 1])
            with left:
                if row["tracked_in_5w"]:
                    percent = min(row["pct"], 100) if pd.notna(row["pct"]) else 0
                    text = f"{row['indicator']} | {row['progress']:,.0f} / {row['target']:,} {row['unit']} ({row['pct']:.0f}%)"
                    st.progress(int(percent), text=text)
                else:
                    st.markdown(
                        f"<div style='color:{MUTED};font-size:14px;padding:6px 0;'>"
                        f"{row['indicator']} | target {row['target']} {row['unit']} "
                        "<i>(not in 5W; track through the coordination log)</i></div>",
                        unsafe_allow_html=True,
                    )
            with right:
                st.caption(row["unit"])
        st.markdown("")

    st.markdown("### Indicator progress vs. target")
    figure = go.Figure()
    for _, row in tracked.iterrows():
        figure.add_trace(go.Bar(
            name=row["indicator"], x=[row["indicator"][:28]], y=[row["progress"]],
            marker_color=OUTPUT_COLORS[row["output"]], showlegend=False,
        ))
        figure.add_trace(go.Scatter(
            x=[row["indicator"][:28]], y=[row["target"]], mode="markers",
            marker=dict(symbol="line-ew", size=28, color=NAVY, line_width=3), showlegend=False,
        ))
    figure.update_layout(height=380, plot_bgcolor="white", paper_bgcolor="white",
                         yaxis_title="People / units reached", margin=dict(t=10, b=120))
    st.plotly_chart(figure, width="stretch")
    st.caption("Bars show reported progress; navy markers show targets. Coordination and feedback indicators need manual tracking.")

    with st.expander("How reach is calculated"):
        st.markdown("""
- Activity rows are mapped to one of the five Programme Document outputs. School, CFS, and health-facility locations take priority for Output 4.
- Water, sanitation, and learning-space reach is summed from reported beneficiaries.
- Hygiene promotion and critical-supply rows can repeat the same people across item types. For these, the largest reported reach per Palika and indicator is counted once.
- Unmapped activities are excluded from totals and listed on the Excel export's Unmapped Activities tab.
- Output 1 coordination indicators are not recorded in the 5W tool and need a separate coordination log.
        """)

elif page == "Activity monitoring":
    st.title("Activity monitoring")
    st.caption("Chay-Ya Nepal and UNICEF records only. Explore activities by location, reporting window, and status.")

    output_options = sorted(df["output"].dropna().unique().tolist())
    status_options = sorted(df["status"].dropna().unique().tolist())
    partner_options = sorted(df["partner"].dropna().unique().tolist())
    activity_options = sorted(df["activity"].dropna().unique().tolist())
    f1, f2, f3, f4, f5 = st.columns(5)
    selected_palikas = f1.multiselect("Palika", PALIKAS, default=PALIKAS)
    selected_outputs = f2.multiselect(
        "Output", output_options, default=output_options,
        format_func=lambda value: f"Output {int(value)}",
    )
    selected_status = f3.multiselect("Activity status", status_options, default=status_options)
    selected_partners = f4.multiselect("Implementing partner", partner_options, default=partner_options)
    selected_activities = f5.multiselect("Activity", activity_options, default=activity_options)

    filtered = df[
        df["municipality"].isin(selected_palikas)
        & df["output"].isin(selected_outputs)
        & df["status"].isin(selected_status)
        & df["partner"].isin(selected_partners)
        & df["activity"].isin(selected_activities)
    ].copy()
    start_dates = pd.to_datetime(df["start_date"], format="%d-%b-%Y", errors="coerce")
    if start_dates.notna().any():
        minimum_date, maximum_date = start_dates.min().date(), start_dates.max().date()
        with st.expander("Filter by activity start date", expanded=False):
            selected_dates = st.date_input(
                "Reporting window", value=(minimum_date, maximum_date),
                min_value=minimum_date, max_value=maximum_date, format="DD/MM/YYYY",
            )
        if isinstance(selected_dates, (tuple, list)) and len(selected_dates) == 2:
            record_dates = pd.to_datetime(filtered["start_date"], format="%d-%b-%Y", errors="coerce")
            filtered = filtered[record_dates.dt.date.between(selected_dates[0], selected_dates[1])]

    filtered_palika = build_palika_summary(filtered)
    filtered_palika = filtered_palika[filtered_palika["palika"].isin(selected_palikas)]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Activity records", f"{len(filtered):,}")
    c2.metric(
        "People reached", f"{filtered_palika['people_reached'].sum():,.0f}",
        help="Uses the dashboard's de-duplication rules for repeated supply and hygiene rows.",
    )
    c3.metric("Ongoing", f"{int(filtered['status'].eq('Ongoing').sum()):,}")
    c4.metric("Completed", f"{int(filtered['status'].eq('Completed').sum()):,}")

    st.markdown("### Reach by Palika and Output")
    reach_by_output = build_palika_output_summary(filtered)
    reach_by_output = reach_by_output[reach_by_output["municipality"].isin(selected_palikas)]
    if len(reach_by_output):
        reach_by_output["Output"] = reach_by_output["output"].map(lambda value: f"Output {int(value)}")
        reach_figure = px.bar(
            reach_by_output, x="municipality", y="progress", color="Output",
            color_discrete_map={f"Output {key}": value for key, value in OUTPUT_COLORS.items()},
            labels={"progress": "People reached", "municipality": ""},
        )
        reach_figure.update_layout(height=360, plot_bgcolor="white", paper_bgcolor="white",
                                   legend_title="", margin=dict(t=12, b=40))
        st.plotly_chart(reach_figure, width="stretch")
    else:
        st.info("No matching activity for this filter combination.")

    left_chart, right_chart = st.columns(2)
    with left_chart:
        st.markdown("### Activity status")
        status_counts = filtered["status"].fillna("Not reported").value_counts().rename_axis("Status").reset_index(name="Records")
        if len(status_counts):
            status_figure = px.pie(
                status_counts, names="Status", values="Records", hole=0.62,
                color_discrete_sequence=["#159488", "#1CABE2", "#E1922E", "#98A8A4"],
            )
            status_figure.update_layout(height=300, plot_bgcolor="white", paper_bgcolor="white",
                                        margin=dict(t=8, b=8), legend_title="")
            st.plotly_chart(status_figure, width="stretch")
        else:
            st.info("No status records match these filters.")
    with right_chart:
        st.markdown("### Records by start month")
        trend = filtered.assign(
            _date=pd.to_datetime(filtered["start_date"], format="%d-%b-%Y", errors="coerce")
        ).dropna(subset=["_date"])
        if len(trend):
            trend["Month"] = trend["_date"].dt.to_period("M").astype(str)
            monthly = trend.groupby("Month").size().reset_index(name="Activity records")
            trend_figure = px.line(monthly, x="Month", y="Activity records", markers=True,
                                   color_discrete_sequence=["#1CABE2"])
            trend_figure.update_layout(height=300, plot_bgcolor="white", paper_bgcolor="white",
                                       margin=dict(t=8, b=8))
            st.plotly_chart(trend_figure, width="stretch")
        else:
            st.info("No dated activity records match these filters.")

    st.markdown("### Reporting coverage by Output and Palika")
    coverage_source = filtered.dropna(subset=["output"]).copy()
    coverage_source["Output"] = coverage_source["output"].map(lambda value: f"Output {int(value)}")
    coverage = pd.crosstab(coverage_source["Output"], coverage_source["municipality"]).reindex(
        columns=selected_palikas, fill_value=0,
    )
    if not coverage.empty and len(coverage.columns):
        coverage_figure = px.imshow(
            coverage, text_auto=True, aspect="auto",
            color_continuous_scale=["#EDF3F1", "#159488"],
            labels={"x": "Palika", "y": "Output", "color": "Activity rows"},
        )
        coverage_figure.update_layout(height=250, margin=dict(t=8, b=8), coloraxis_showscale=False)
        st.plotly_chart(coverage_figure, width="stretch")
    else:
        st.info("No mapped reporting coverage for this filter combination.")

    st.markdown("### Demographic reach")
    if not filtered_palika.empty:
        demographic = filtered_palika[
            ["palika", "girls", "boys", "women", "men", "elderly_women", "elderly_men", "pwd"]
        ].set_index("palika")
        demographic.index = demographic.index.str.replace(" Gaunpalika", "")
        st.bar_chart(demographic, color=["#C77A1E", "#1CABE2", "#159488", "#7C5CBF", "#E1922E", "#64748B", "#A6362C"])
    st.caption("Demographic figures follow the same de-duplication logic as the programme overview.")

    st.markdown("### Activity log")
    display_columns = [
        "partner", "output", "indicator", "municipality", "ward", "holding_centre",
        "type_specific_location", "activity", "activity_description", "modality", "status",
        "people_targeted", "people_reached", "hh_targeted", "hh_reached", "girls", "boys",
        "women", "men", "elderly_women", "elderly_men", "pwd", "start_date", "end_date", "notes",
    ]
    display_labels = {
        "partner": "Implementing partner", "output": "Output", "indicator": "Mapped indicator",
        "municipality": "Palika", "ward": "Ward", "holding_centre": "Holding centre",
        "type_specific_location": "Specific location", "activity": "Activity",
        "activity_description": "Activity description", "modality": "Modality", "status": "Status",
        "people_targeted": "People targeted", "people_reached": "People reached",
        "hh_targeted": "Households targeted", "hh_reached": "Households reached",
        "girls": "Girls (<18)", "boys": "Boys (<18)", "women": "Women (18+)", "men": "Men (18+)",
        "elderly_women": "Elderly women (60+)", "elderly_men": "Elderly men (60+)",
        "pwd": "People with disabilities", "start_date": "Start date", "end_date": "End date",
        "notes": "Notes",
    }
    st.dataframe(
        filtered[display_columns].rename(columns=display_labels),
        width="stretch", height=430, hide_index=True,
    )

else:
    st.title("Project site map")
    st.caption("Georeferenced sites from the Chay-Ya Nepal and UNICEF Google My Map.")
    if hasattr(st, "iframe"):
        st.iframe(MAP_EMBED_URL, height=620)
    else:
        st.components.v1.iframe(MAP_EMBED_URL, height=620, scrolling=True)
    st.link_button("Open map in Google My Maps", MAP_EDIT_URL)
    st.caption("Map visibility follows Google My Maps sharing settings. Use view access for dashboard viewers.")

    st.markdown("### Related 5W activities")
    st.caption(
        "Filter the 5W activity register below. The map pins are from the shared My Maps layer; "
        "they are not automatically joined to 5W rows because the source export has no GPS coordinates."
    )
    map_data = df.copy()
    map_data["output_label"] = map_data["output"].map(
        lambda value: f"Output {int(value)}" if pd.notna(value) else "Unmapped"
    )
    map_palika_options = sorted(map_data["municipality"].dropna().unique().tolist())
    map_output_options = sorted(map_data["output_label"].unique().tolist())
    map_status_options = sorted(map_data["status"].dropna().unique().tolist())
    present_partners = [partner for partner in PARTNER_SCOPE if partner in map_data["partner"].unique()]
    m1, m2, m3, m4 = st.columns(4)
    map_palikas = m1.multiselect("Palika", map_palika_options, default=map_palika_options, key="map_palikas")
    map_outputs = m2.multiselect("Output", map_output_options, default=map_output_options, key="map_outputs")
    map_statuses = m3.multiselect("Activity status", map_status_options, default=map_status_options, key="map_statuses")
    map_partners = m4.multiselect("Organization", PARTNER_SCOPE, default=present_partners, key="map_partners")

    map_filtered = map_data[
        map_data["municipality"].isin(map_palikas)
        & map_data["output_label"].isin(map_outputs)
        & map_data["status"].isin(map_statuses)
        & map_data["partner"].isin(map_partners)
    ].copy()
    map_summary = build_palika_summary(map_filtered)
    map_summary = map_summary[map_summary["palika"].isin(map_palikas)]
    location_text = (
        map_filtered["type_specific_location"].fillna("").astype(str).str.strip().ne("")
        | map_filtered["holding_centre"].fillna("").astype(str).str.strip().ne("")
    )
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Activity records", f"{len(map_filtered):,}")
    k2.metric("Palikas represented", f"{map_filtered['municipality'].nunique():,}")
    k3.metric("Records with site text", f"{int(location_text.sum()):,}")
    k4.metric("People reached", f"{map_summary['people_reached'].sum():,.0f}")

    map_columns = [
        "partner", "output_label", "indicator", "municipality", "ward", "holding_centre",
        "type_specific_location", "activity", "activity_description", "status",
        "people_reached", "start_date", "end_date",
    ]
    map_labels = {
        "partner": "Organization", "output_label": "Output", "indicator": "Mapped indicator",
        "municipality": "Palika", "ward": "Ward", "holding_centre": "Holding centre",
        "type_specific_location": "Specific location", "activity": "Activity",
        "activity_description": "Activity description", "status": "Status",
        "people_reached": "People reached", "start_date": "Start date", "end_date": "End date",
    }
    st.dataframe(map_filtered[map_columns].rename(columns=map_labels), width="stretch", hide_index=True)
