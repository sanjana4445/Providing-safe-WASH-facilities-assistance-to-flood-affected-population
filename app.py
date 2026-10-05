import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

from data_processing import (
    FIVEW_COLUMNS, INDICATORS_DF, OUTPUT_COLORS, PALIKAS,
    build_indicator_summary, build_monitoring_workbook, build_palika_output_summary,
    build_palika_summary, load_5w,
)

st.set_page_config(page_title="Rasuwa WASH Response", page_icon="\U0001F4A7", layout="wide")

UNICEF_BLUE = "#009FE3"
CHAYA_GREEN = "#26734D"
COMPLETED_GREEN = "#25815A"
ONGOING_AMBER = "#D28B27"
NAVY = "#183A46"
MUTED = "#64747A"
PAGE_BG = "#F4F7F6"
ORG_COLORS = {"UNICEF": UNICEF_BLUE, "Chay-Ya Nepal": CHAYA_GREEN}
STATUS_COLORS = {"Completed": COMPLETED_GREEN, "Ongoing": ONGOING_AMBER}
PARTNER_ALIASES = {
    "unicef": "UNICEF", "unicef nepal": "UNICEF",
    "chay ya": "Chay-Ya Nepal", "chay ya nepal": "Chay-Ya Nepal",
}
PARTNER_SCOPE = ["Chay-Ya Nepal", "UNICEF"]
MAP_ID = "1qtThPTqZuAuCMHl_Oqkq-0OW-ZFdjsU"
MAP_EMBED_URL = f"https://www.google.com/maps/d/embed?mid={MAP_ID}"
MAP_EDIT_URL = f"https://www.google.com/maps/d/u/0/edit?mid={MAP_ID}"
PAGE_OPTIONS = [
    "Overview", "Palika detail", "Activities by output",
    "Beneficiary demographics", "Beneficiary explorer", "Project map",
]
FIELD_LABELS = {
    "lead_agency": "Lead agency", "partner": "Implementing partner", "donor": "Donor",
    "province": "Province", "district": "District", "municipality": "Palika", "ward": "Ward",
    "holding_centre": "Holding centre / displacement site", "type_specific_location": "Specific location",
    "location_type": "Location type", "sector": "Sector", "aor": "Area of responsibility",
    "response_plan": "Disaster / response plan", "activity": "Activity",
    "activity_description": "Activity description", "modality": "Response modality",
    "activity_indicator": "Activity indicator", "activity_indicator_unit": "Activity indicator unit",
    "activity_target": "Activity target", "activity_reached": "Activity reached",
    "relief_items": "Relief items", "relief_item_description": "Relief item description",
    "relief_item_unit": "Relief item unit", "relief_items_planned": "Relief items planned",
    "relief_items_distributed": "Relief items distributed", "cash_delivery_mechanism": "Cash delivery mechanism",
    "cash_conditionality": "Cash conditionality", "fsp_delivery_agent": "FSP / delivery agent",
    "cash_beneficiary_unit": "Cash beneficiary unit", "cash_transfer_value_per_unit": "Cash transfer value per unit (USD)",
    "cash_frequency": "Cash frequency", "total_expected_cash_transfer": "Expected cash transfer (USD)",
    "total_disbursed_amount": "Disbursed amount (USD)", "hh_targeted": "Households targeted",
    "people_targeted": "People targeted", "hh_reached": "Households reached",
    "people_reached": "People reached", "girls": "Girls (<18)", "boys": "Boys (<18)",
    "women": "Women (18+)", "men": "Men (18+)", "elderly_women": "Elderly women (60+)",
    "elderly_men": "Elderly men (60+)", "pwd": "People with disabilities",
    "organisations_institutions": "Organisations / institutions", "status": "Activity status",
    "start_date": "Activity start date", "end_date": "Activity end date", "notes": "Notes",
    "edit_date": "Edit date",
}
SOURCE_COLUMNS = list(FIVEW_COLUMNS.values())
FULL_REGISTER_COLUMNS = SOURCE_COLUMNS + ["output", "indicator"]
DETAIL_COLUMNS = [
    "lead_agency", "partner", "district", "municipality", "ward", "location_type",
    "holding_centre", "type_specific_location", "sector", "activity", "activity_description",
    "modality", "activity_indicator", "activity_indicator_unit", "activity_target", "activity_reached",
    "relief_items", "relief_item_unit", "relief_items_planned", "relief_items_distributed",
    "people_targeted", "people_reached", "hh_targeted", "hh_reached", "status", "start_date", "end_date",
]

st.markdown(f"""
<style>
.stApp {{ background: {PAGE_BG}; color: #24373D; }}
h1, h2, h3 {{ color: {NAVY}; letter-spacing: 0; }}
.block-container {{ padding-top: 1.2rem; padding-bottom: 3rem; max-width: 1500px; }}
div[data-testid="stSidebar"] {{ background: #EAF0EE; }}
div[data-testid="stMetric"] {{
    background: #FFFFFF; border: 1px solid #DCE6E2; border-radius: 6px;
    padding: 12px 15px; box-shadow: 0 2px 8px rgba(24,58,70,0.035);
}}
div[data-testid="stMetricValue"] {{ color: {NAVY}; }}
div[data-testid="stRadio"] > label {{ display: none; }}
div[data-testid="stRadio"] div[role="radiogroup"] {{ gap: 0.35rem; flex-wrap: wrap; }}
div[data-testid="stRadio"] div[role="radiogroup"] label {{
    border: 1px solid #DCE6E2; border-radius: 5px; background: #FFFFFF; padding: 0.35rem 0.7rem;
}}
div[data-testid="stRadio"] div[role="radiogroup"] label:has(input:checked) {{
    background: {NAVY}; border-color: {NAVY}; color: white;
}}
</style>
""", unsafe_allow_html=True)

st.sidebar.title("\U0001F4A7 Rasuwa WASH")
st.sidebar.caption("Chay-Ya Nepal  |  UNICEF Nepal")
st.sidebar.markdown("### Data source")
uploaded = st.sidebar.file_uploader(
    "Upload latest 5W export", type=["xlsx"],
    help="The dashboard reads the bundled UNICEF workbook unless a newer export is uploaded.",
)
DEFAULT_PATH = "Rasuwa_-_UNICEF_WASH_NEPAL_5Ws_Data_Entry.xlsx"


@st.cache_data(show_spinner="Reading the 5W workbook…")
def get_data(file_bytes_or_path):
    return load_5w(file_bytes_or_path)


try:
    df = get_data(uploaded if uploaded is not None else DEFAULT_PATH)
except Exception as exc:
    st.error(f"Could not read the 5W workbook: {exc}")
    st.stop()

normalized_partners = (
    df["partner"].astype("string").str.casefold()
    .str.replace(r"[^a-z0-9]+", " ", regex=True).str.strip()
)
df["partner"] = normalized_partners.map(PARTNER_ALIASES)
excluded_partner_rows = int(df["partner"].isna().sum())
df = df[df["partner"].notna()].copy()
indicator_summary = build_indicator_summary(df)
output_labels = INDICATORS_DF[["output", "output_label"]].drop_duplicates().sort_values("output")
output_names = dict(zip(output_labels["output"], output_labels["output_label"]))
output_numbers = sorted(INDICATORS_DF["output"].unique().tolist())
active_output_numbers = sorted(df["output"].dropna().astype(int).unique().tolist())
palika_summary = build_palika_summary(df)
unmapped = df[df["output"].isna()]

st.sidebar.markdown("---")
st.sidebar.metric("5W records in scope", f"{len(df):,}")
st.sidebar.caption("Only UNICEF and Chay-Ya Nepal records are included.")
if excluded_partner_rows:
    st.sidebar.caption(f"{excluded_partner_rows} record(s) from other partners excluded.")
if len(unmapped):
    st.sidebar.warning(f"{len(unmapped)} activity row(s) are not mapped to an output; review the Excel export.")
st.sidebar.caption(f"Loaded {datetime.now().strftime('%d %b %Y, %H:%M')}")
st.sidebar.download_button(
    "Download Excel monitoring pack",
    data=build_monitoring_workbook(df),
    file_name=f"rasuwa_wash_5w_monitoring_{datetime.now():%Y%m%d}.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    use_container_width=True,
)

st.markdown(
    f"<div style='border-left:4px solid {UNICEF_BLUE}; padding-left:12px; margin:2px 0 8px;'>"
    f"<span style='color:{UNICEF_BLUE};font-weight:700;'>UNICEF</span>"
    f"<span style='color:#89979A;padding:0 8px;'>|</span>"
    f"<span style='color:{CHAYA_GREEN};font-weight:700;'>Chay-Ya Nepal</span>"
    "<span style='color:#64747A;padding-left:10px;'>Rasuwa WASH response monitoring</span></div>",
    unsafe_allow_html=True,
)
page = st.radio("Dashboard section", PAGE_OPTIONS, horizontal=True, label_visibility="collapsed")


def display_register(frame, full=False, height=500):
    table = frame.copy()
    table["mapped_output"] = table["output"].map(
        lambda value: f"Output {int(value)}" if pd.notna(value) else "Unmapped"
    )
    table = table.drop(columns=["output"]).rename(columns={
        **FIELD_LABELS, "indicator": "Mapped PD indicator", "mapped_output": "Mapped PD output",
    })
    columns = [FIELD_LABELS[col] for col in SOURCE_COLUMNS] + ["Mapped PD output", "Mapped PD indicator"]
    if not full:
        columns = [FIELD_LABELS[col] for col in DETAIL_COLUMNS] + ["Mapped PD output", "Mapped PD indicator"]
    return table.reindex(columns=columns)


def palika_metric_table(frame):
    summary = build_palika_summary(frame).set_index("palika")
    summary.index = summary.index.str.replace(" Gaunpalika", "", regex=False)
    return summary


def render_palika_bar(frame, measure, chart_key):
    if measure == "People reached (deduplicated)":
        values = palika_metric_table(frame)["people_reached"]
    elif measure == "Households reached (deduplicated)":
        values = palika_metric_table(frame)["households_reached"]
    elif measure == "Activity records":
        values = frame.groupby("municipality").size()
    else:
        source_column = {
            "People targeted (row total)": "people_targeted",
            "Households targeted (row total)": "hh_targeted",
            "Relief items distributed": "relief_items_distributed",
        }[measure]
        values = frame.groupby("municipality")[source_column].sum(min_count=1)
    values = values.reindex(PALIKAS, fill_value=0)
    chart_data = pd.DataFrame({"Palika": values.index, measure: values.values})
    chart_data["Palika"] = chart_data["Palika"].str.replace(" Gaunpalika", "", regex=False)
    chart_data[measure] = chart_data[measure].fillna(0)
    palika_colors = {
        "Gosaikunda": UNICEF_BLUE, "Uttargaya": CHAYA_GREEN,
        "Kalika": "#D28B27", "Aamachhodingmo": "#597D8A",
    }
    figure = px.bar(
        chart_data, x=measure, y="Palika", orientation="h", color="Palika",
        color_discrete_map=palika_colors, text=measure,
        labels={measure: measure, "Palika": ""},
    )
    figure.update_layout(
        height=330, plot_bgcolor="white", paper_bgcolor="white", showlegend=False,
        margin=dict(l=8, r=18, t=12, b=24), yaxis={"categoryorder": "total ascending"},
    )
    figure.update_traces(texttemplate="%{x:,.0f}", textposition="outside", cliponaxis=False)
    st.plotly_chart(figure, width="stretch", key=chart_key)


if page == "Overview":
    st.title("Rasuwa WASH response")
    st.caption("Five programme outputs · ten targets · UNICEF 5W activity progress")
    tracked = indicator_summary[indicator_summary["tracked_in_5w"]].copy()
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Programme outputs", "5")
    k2.metric("PD indicators", "10")
    k3.metric("Tracked in 5W", f"{int(tracked.shape[0])} / 10")
    k4.metric("Activity records", f"{len(df):,}")

    st.markdown("### Outputs")
    output_cards = st.columns(5)
    for column, (_, item) in zip(output_cards, output_labels.iterrows()):
        indicator_count = int((indicator_summary["output"] == item["output"]).sum())
        short_label = item["output_label"].split("\u2013", 1)[-1].strip()
        with column:
            st.markdown(
                f"<div style='background:#fff;border:1px solid #DCE6E2;border-top:3px solid {OUTPUT_COLORS[item['output']]};"
                "border-radius:5px;padding:10px 11px;min-height:92px;'>"
                f"<div style='font-size:12px;color:{MUTED};'>OUTPUT {int(item['output'])}</div>"
                f"<div style='font-size:13px;font-weight:650;color:{NAVY};margin-top:5px;'>{short_label}</div>"
                f"<div style='font-size:11px;color:{MUTED};margin-top:6px;'>{indicator_count} indicators</div></div>",
                unsafe_allow_html=True,
            )

    st.markdown("### Ten-indicator target tracker")
    tracker = indicator_summary.copy()
    tracker["Remaining"] = (tracker["target"] - tracker["progress"]).clip(lower=0)
    tracker["Progress (%)"] = tracker["pct"].where(tracker["tracked_in_5w"])
    tracker["Tracking"] = tracker.apply(
        lambda row: "Manual" if not row["tracked_in_5w"] else (
            "Target reached" if row["progress"] >= row["target"] else
            "In progress" if row["progress"] > 0 else "Not started"
        ), axis=1,
    )
    tracker_view = tracker.rename(columns={
        "output": "Output #", "indicator": "Indicator", "unit": "Unit", "target": "Target",
        "progress": "Progress", "tracked_in_5w": "In 5W",
    })[["Output #", "Indicator", "Target", "Progress", "Remaining", "Progress (%)", "Unit", "Tracking"]]
    st.dataframe(tracker_view, width="stretch", hide_index=True, height=395)

    st.markdown("### Progress by indicator")
    chart_data = tracked.copy()
    chart_data["Indicator"] = chart_data["indicator"]
    chart_data["Progress (%)"] = chart_data["pct"]
    chart_data["Output"] = chart_data["output"].map(lambda number: f"Output {int(number)}")
    color_map = {f"Output {number}": color for number, color in OUTPUT_COLORS.items()}
    overview_chart = px.bar(
        chart_data.sort_values("Progress (%)"), x="Progress (%)", y="Indicator", orientation="h",
        color="Output", color_discrete_map=color_map, text="Progress (%)",
        labels={"Progress (%)": "Target progress", "Indicator": ""},
    )
    overview_chart.add_vline(x=100, line_dash="dot", line_color=CHAYA_GREEN, annotation_text="Target")
    overview_chart.update_traces(texttemplate="%{x:.0f}%", textposition="outside", cliponaxis=False)
    overview_chart.update_layout(
        height=410, barmode="group", plot_bgcolor="white", paper_bgcolor="white",
        legend_title="", margin=dict(l=8, r=46, t=18, b=30),
    )
    st.plotly_chart(overview_chart, width="stretch", key="overview_progress_chart")
    st.caption("Chart includes the seven indicators tracked in 5W. Three coordination/feedback indicators require separate manual tracking.")

elif page == "Palika detail":
    st.title("Palika-wise 5W detail")
    st.caption("Compare reported activity and reach across the four programme Palikas; open the register for every source field.")
    c1, c2, c3 = st.columns(3)
    selected_palikas = c1.multiselect("Palika", PALIKAS, default=PALIKAS, key="palika_filter")
    available_outputs = sorted(df["output"].dropna().unique().tolist())
    selected_outputs = c2.multiselect(
        "Output", available_outputs, default=available_outputs, key="palika_output_filter",
        format_func=lambda number: f"Output {int(number)}",
    )
    statuses = sorted(df["status"].dropna().unique().tolist())
    selected_status = c3.multiselect("Activity status", statuses, default=statuses, key="palika_status_filter")
    filtered = df[
        df["municipality"].isin(selected_palikas)
        & df["output"].isin(selected_outputs)
        & df["status"].isin(selected_status)
    ].copy()

    reach_values = palika_metric_table(filtered)
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Activity rows", f"{len(filtered):,}")
    k2.metric("People reached", f"{reach_values['people_reached'].sum():,.0f}")
    k3.metric("Households reached", f"{reach_values['households_reached'].sum():,.0f}")
    k4.metric("Palikas reporting", f"{int((reach_values['activities'] > 0).sum())} / 4")

    measure_options = [
        "People reached (deduplicated)", "Households reached (deduplicated)", "Activity records",
        "People targeted (row total)", "Households targeted (row total)", "Relief items distributed",
    ]
    measure = st.selectbox("Compare Palikas by", measure_options, key="palika_measure")
    render_palika_bar(filtered, measure, "palika_metric_chart")
    if measure.endswith("row total"):
        st.caption("Target values are shown as reported per 5W activity row and may repeat across item rows.")

    st.markdown("### Activity register")
    st.dataframe(display_register(filtered), width="stretch", height=440, hide_index=True)
    with st.expander("Show every source 5W field"):
        st.dataframe(display_register(filtered, full=True, height=550), width="stretch", height=550, hide_index=True)

elif page == "Activities by output":
    st.title("Activities by programme output")
    st.caption("Unpack each output into its reported activity types, status, and reach.")
    default_output = active_output_numbers[0] if active_output_numbers else output_numbers[0]
    selected_output = st.selectbox(
        "Programme output", output_numbers, index=output_numbers.index(default_output),
        format_func=lambda number: output_names[number], key="activity_output",
    )
    output_frame = df[df["output"] == selected_output].copy()
    activity_options = ["All activities"] + sorted(output_frame["activity"].dropna().unique().tolist())
    selected_activity = st.selectbox("Activity type", activity_options, key="activity_type")
    if selected_activity != "All activities":
        output_frame = output_frame[output_frame["activity"] == selected_activity]
    activity_statuses = sorted(output_frame["status"].dropna().unique().tolist())
    selected_activity_status = st.multiselect(
        "Activity status", activity_statuses, default=activity_statuses, key="activity_status",
    )
    output_frame = output_frame[output_frame["status"].isin(selected_activity_status)]

    unique_reach = build_palika_output_summary(output_frame)
    unique_reach = unique_reach[unique_reach["output"] == selected_output]["progress"].sum()
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Activity rows", f"{len(output_frame):,}")
    k2.metric("Palikas", f"{output_frame['municipality'].nunique():,}")
    k3.metric("People reached", f"{unique_reach:,.0f}", help="Deduplicated using the programme indicator rules.")
    k4.metric("Completed", f"{int(output_frame['status'].eq('Completed').sum()):,}")

    activity_measure = st.selectbox(
        "Bar chart measure", ["Activity records", "Reported people reached", "Relief items distributed"],
        key="activity_chart_measure",
    )
    if output_frame.empty:
        st.info("No activity records for this output/filter combination.")
    else:
        if activity_measure == "Activity records":
            x_label = "Activity records"
            activity_chart_data = output_frame.groupby(["activity", "status"]).size().reset_index(name=x_label)
        elif activity_measure == "Reported people reached":
            x_label = "Reported people reached"
            activity_chart_data = output_frame.groupby(["activity", "status"])["people_reached"].sum(min_count=1).reset_index(name=x_label)
        else:
            x_label = "Relief items distributed"
            activity_chart_data = output_frame.groupby(["activity", "status"])["relief_items_distributed"].sum(min_count=1).reset_index(name=x_label)
        activity_chart_data = activity_chart_data.fillna({x_label: 0})
        activity_chart_data = activity_chart_data.sort_values(x_label)
        activity_chart_data["Activity"] = activity_chart_data["activity"]
        activity_chart = px.bar(
            activity_chart_data, x=x_label, y="Activity", orientation="h",
            color="status", color_discrete_map=STATUS_COLORS, text=x_label,
            labels={x_label: x_label, "Activity": "", "status": "Status"}, barmode="stack",
        )
        activity_chart.update_traces(texttemplate="%{x:,.0f}", textposition="outside", cliponaxis=False)
        activity_chart.update_layout(
            height=max(320, 44 * len(activity_chart_data)), plot_bgcolor="white", paper_bgcolor="white",
            showlegend=False, margin=dict(l=8, r=34, t=16, b=24),
        )
        st.plotly_chart(activity_chart, width="stretch", key="output_activity_chart")
        if activity_measure == "Reported people reached":
            st.caption("Activity bars show row-reported reach. Use the deduplicated KPI above for programme totals.")

    st.markdown("### Matching 5W records")
    st.dataframe(display_register(output_frame), width="stretch", height=420, hide_index=True)
    with st.expander("Show every source 5W field"):
        st.dataframe(display_register(output_frame, full=True, height=550), width="stretch", height=550, hide_index=True)

elif page == "Beneficiary demographics":
    st.title("Beneficiary demographics")
    st.caption("Reported sex and age-group reach by Palika. Elderly and disability counts are shown separately to avoid double-counting overlapping groups.")
    demo_palikas = st.multiselect("Palika", PALIKAS, default=PALIKAS, key="demo_palikas")
    demo_statuses = sorted(df["status"].dropna().unique().tolist())
    demo_selected_status = st.multiselect("Activity status", demo_statuses, default=demo_statuses, key="demo_status")
    demographic_rows = df[df["municipality"].isin(demo_palikas) & df["status"].isin(demo_selected_status)]
    demo = palika_metric_table(demographic_rows).reindex(
        [palika for palika in PALIKAS if palika.replace(" Gaunpalika", "") in demo_palikas]
    )
    demo.index = demo.index.str.replace(" Gaunpalika", "", regex=False)
    demo_kpis = st.columns(4)
    demo_kpis[0].metric("Girls (<18)", f"{demo['girls'].sum():,.0f}")
    demo_kpis[1].metric("Boys (<18)", f"{demo['boys'].sum():,.0f}")
    demo_kpis[2].metric("Women (18+)", f"{demo['women'].sum():,.0f}")
    demo_kpis[3].metric("Men (18+)", f"{demo['men'].sum():,.0f}")

    demographic_chart_data = (
        demo[["girls", "boys", "women", "men"]]
        .rename(columns={"girls": "Girls (<18)", "boys": "Boys (<18)", "women": "Women (18+)", "men": "Men (18+)"})
        .rename_axis("Palika").reset_index().melt(id_vars="Palika", var_name="Group", value_name="Beneficiaries")
    )
    demographic_chart = px.bar(
        demographic_chart_data, x="Palika", y="Beneficiaries", color="Group", barmode="group",
        color_discrete_map={
            "Girls (<18)": "#E77C62", "Boys (<18)": UNICEF_BLUE,
            "Women (18+)": CHAYA_GREEN, "Men (18+)": "#627B8A",
        },
    )
    demographic_chart.update_layout(height=390, plot_bgcolor="white", paper_bgcolor="white",
                                    legend_title="", margin=dict(t=16, b=24))
    st.plotly_chart(demographic_chart, width="stretch", key="demographic_chart")

    other_groups = demo[["elderly_women", "elderly_men", "pwd"]].rename(columns={
        "elderly_women": "Elderly women (60+)", "elderly_men": "Elderly men (60+)",
        "pwd": "People with disabilities",
    })
    st.markdown("### Additional reported groups")
    st.dataframe(other_groups, width="stretch")

elif page == "Beneficiary explorer":
    st.title("Beneficiary explorer")
    st.caption("Select an output and activity to compare reported reach across Palikas.")
    output_choices = ["All outputs"] + output_numbers
    chosen_output = st.selectbox(
        "Programme output", output_choices,
        format_func=lambda number: "All outputs" if number == "All outputs" else output_names[number],
        key="beneficiary_output",
    )
    beneficiary_rows = df.copy()
    if chosen_output != "All outputs":
        beneficiary_rows = beneficiary_rows[beneficiary_rows["output"] == chosen_output]
    activity_choices = ["All activities"] + sorted(beneficiary_rows["activity"].dropna().unique().tolist())
    chosen_activity = st.selectbox("WASH activity", activity_choices, key="beneficiary_activity")
    if chosen_activity != "All activities":
        beneficiary_rows = beneficiary_rows[beneficiary_rows["activity"] == chosen_activity]
    reach_measure = st.selectbox(
        "Beneficiary measure", ["People reached", "Households reached"], key="beneficiary_measure",
    )
    beneficiary_summary = palika_metric_table(beneficiary_rows)
    summary_column = "people_reached" if reach_measure == "People reached" else "households_reached"
    chart_values = beneficiary_summary[summary_column].copy()
    chart_data = pd.DataFrame({reach_measure: chart_values.values}, index=chart_values.index)
    chart_data.index = chart_data.index.str.replace(" Gaunpalika", "", regex=False)
    chart_data.index.name = "Palika"
    chart_data = chart_data.reset_index()
    total_reach = chart_data[reach_measure].sum()
    k1, k2 = st.columns(2)
    k1.metric(f"Total {reach_measure.lower()}", f"{total_reach:,.0f}")
    k2.metric("Activity rows", f"{len(beneficiary_rows):,}")
    beneficiary_chart = px.bar(
        chart_data, x="Palika", y=reach_measure, color="Palika",
        color_discrete_map={
            "Gosaikunda": UNICEF_BLUE, "Uttargaya": CHAYA_GREEN,
            "Kalika": "#D28B27", "Aamachhodingmo": "#597D8A",
        }, text=reach_measure,
    )
    beneficiary_chart.update_traces(texttemplate="%{y:,.0f}", textposition="outside", cliponaxis=False)
    beneficiary_chart.update_layout(height=390, plot_bgcolor="white", paper_bgcolor="white",
                                   showlegend=False, margin=dict(t=16, b=24))
    st.plotly_chart(beneficiary_chart, width="stretch", key="beneficiary_chart")
    st.caption("Reach follows the dashboard's deduplication rules for hygiene promotion and critical supplies.")
    st.dataframe(chart_data, width="stretch", hide_index=True)

else:
    st.title("Project site map")
    st.caption("Shared Google My Maps layer and the related UNICEF / Chay-Ya activity records.")
    if hasattr(st, "iframe"):
        st.iframe(MAP_EMBED_URL, height=560)
    else:
        st.components.v1.iframe(MAP_EMBED_URL, height=560, scrolling=True)
    st.link_button("Open in Google My Maps", MAP_EDIT_URL)
    st.info("Map pins are not automatically matched to 5W rows: the source 5W export has no GPS coordinates or shared site ID.")
    map_palikas = st.multiselect("Palika", PALIKAS, default=PALIKAS, key="map_palikas")
    map_statuses = sorted(df["status"].dropna().unique().tolist())
    map_selected_statuses = st.multiselect("Activity status", map_statuses, default=map_statuses, key="map_statuses")
    map_rows = df[df["municipality"].isin(map_palikas) & df["status"].isin(map_selected_statuses)]
    st.markdown("### Related 5W register")
    st.dataframe(display_register(map_rows), width="stretch", height=420, hide_index=True)
    with st.expander("Show every source 5W field"):
        st.dataframe(display_register(map_rows, full=True, height=550), width="stretch", height=550, hide_index=True)
