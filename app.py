import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date, datetime
from html import escape
from io import BytesIO
from pathlib import Path

from data_processing import (
    FIVEW_COLUMNS, INDICATORS_DF, OUTPUT_COLORS, PALIKAS,
    build_activity_rollup, build_activity_target_summary,
    build_indicator_summary, build_monitoring_workbook, build_output_reporting_summary,
    build_palika_output_summary,
    build_palika_summary, load_5w,
)
from manual_data import (
    delete_manual_entry, load_manual_entries as read_manual_entries, save_manual_entry,
)

PROJECT_TITLE = "Providing safe WASH facilities & assistance to flood-affected population"
st.set_page_config(page_title=PROJECT_TITLE, page_icon="\U0001F4A7", layout="wide")

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
PROJECT_START = date(2026, 9, 15)
PROJECT_END = date(2026, 12, 31)
MANUAL_INDICATORS = INDICATORS_DF.loc[
    ~INDICATORS_DF["tracked_in_5w"], ["output", "indicator", "unit"]
].to_dict(orient="records")
MANUAL_DATA_PATH = Path(__file__).with_name("manual_entries.csv")
MANUAL_GPS_DATA_PATH = Path(__file__).with_name("manual_gps_locations.csv")
PAGE_OPTIONS = [
    "Overview", "Palika detail", "Activities by output",
    "Beneficiary demographics", "Beneficiary explorer", "Manual activity entry", "Planning", "Project map",
]
PAGE_TITLES = {
    "Overview": "\U0001F4A7 WASH response overview",
    "Palika detail": "\U0001F4CD Palika-wise activity",
    "Activities by output": "\U0001F9ED Activities by programme output",
    "Beneficiary demographics": "\U0001F465 Beneficiary demographics",
    "Beneficiary explorer": "\U0001F50E Beneficiary explorer",
    "Manual activity entry": "\u270D Manual activity entry",
    "Planning": "\U0001F3AF Activity prioritization",
    "Project map": "\U0001F5FA Project site map",
}
FIELD_LABELS = {
    "source_row": "Source 5W row",
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
    "subindicator": "Mapped sub-indicator",
}
SOURCE_COLUMNS = list(FIVEW_COLUMNS.values())
FULL_REGISTER_COLUMNS = SOURCE_COLUMNS + ["output", "indicator", "subindicator"]
DETAIL_COLUMNS = [
    "lead_agency", "partner", "district", "municipality", "ward", "location_type",
    "holding_centre", "type_specific_location", "sector", "activity", "activity_description",
    "modality", "activity_indicator", "activity_indicator_unit", "activity_target", "activity_reached",
    "relief_items", "relief_item_unit", "relief_items_planned", "relief_items_distributed",
    "people_targeted", "people_reached", "hh_targeted", "hh_reached", "status", "start_date", "end_date",
    "subindicator",
]

st.markdown(f"""
<style>
.stApp {{ background: {PAGE_BG}; color: #24373D; }}
h1, h2, h3 {{ color: {NAVY}; letter-spacing: -0.025em; }}
h1 {{ font-size: clamp(1.8rem, 3vw, 2.45rem); line-height: 1.15; margin-bottom: 0.35rem; }}
h2 {{ font-size: 1.45rem; margin-top: 1.35rem; }}
h3 {{ font-size: 1.1rem; }}
.project-title {{ color: {NAVY}; font-size: clamp(1.25rem, 2.2vw, 1.8rem); font-weight: 700; line-height: 1.2; margin-bottom: 0.85rem; }}
.block-container {{ padding: 2.5rem 2.2rem 3rem; max-width: 1440px; }}
div[data-testid="stSidebar"] {{ background: #EAF0EE; border-right: 1px solid #DCE6E2; }}
div[data-testid="stSidebar"] h2 {{ font-size: 1.15rem; }}
div[data-testid="stCaptionContainer"] {{ color: {MUTED}; }}
div[data-testid="stMetric"] {{
    background: linear-gradient(145deg, #FFFFFF 15%, #F8FBFA 100%);
    border: 1px solid #DCE6E2; border-radius: 12px;
    padding: 15px 17px; box-shadow: 0 4px 14px rgba(24,58,70,0.055);
}}
div[data-testid="stMetricValue"] {{ color: {NAVY}; }}
div[data-testid="stRadio"] > label {{ display: none; }}
div[data-testid="stRadio"] div[role="radiogroup"] {{ gap: 0.45rem; row-gap: 0.45rem; flex-wrap: wrap; }}
div[data-testid="stRadio"] div[role="radiogroup"] label {{
    border: 1px solid #DCE6E2; border-radius: 999px; background: #FFFFFF;
    padding: 0.4rem 0.85rem; white-space: nowrap; transition: all 120ms ease;
}}
div[data-testid="stRadio"] div[role="radiogroup"] label:has(input:checked) {{
    background: {NAVY}; border-color: {NAVY}; color: #FFFFFF;
    box-shadow: 0 3px 10px rgba(24,58,70,0.18);
}}
div[data-testid="stPlotlyChart"] {{ background: #FFFFFF; border: 1px solid #E2EAE7; border-radius: 12px; padding: 0.4rem; }}
div[data-testid="stDataFrame"] {{ border: 1px solid #E2EAE7; border-radius: 10px; overflow: hidden; }}
div[data-testid="stFileUploader"] {{ background: #FFFFFF; border: 1px dashed #B8CBC5; border-radius: 10px; padding: 0.4rem; }}
div[data-testid="stButton"] button, div[data-testid="stDownloadButton"] button,
div[data-testid="stFormSubmitButton"] button {{ border-radius: 9px; font-weight: 600; }}
.output-progress-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(225px, 1fr)); gap: 14px; margin: 0.5rem 0 1.2rem; }}
.output-progress-card {{ background: #FFFFFF; border: 1px solid #DCE6E2; border-top: 4px solid; border-radius: 12px; padding: 15px; box-shadow: 0 4px 14px rgba(24,58,70,0.055); }}
.output-progress-title {{ color: {NAVY}; font-size: 1rem; font-weight: 700; margin-bottom: 0.15rem; }}
.output-progress-subtitle {{ color: {MUTED}; font-size: 0.75rem; margin-bottom: 0.9rem; }}
.output-indicator {{ border-top: 1px solid #E7EEEB; padding: 0.75rem 0 0.2rem; margin-top: 0.65rem; }}
.output-indicator:first-of-type {{ border-top: 0; padding-top: 0; margin-top: 0; }}
.output-indicator-heading {{ display: flex; align-items: flex-start; justify-content: space-between; gap: 8px; color: #24373D; font-size: 0.82rem; font-weight: 650; line-height: 1.3; }}
.output-indicator-status {{ flex: 0 0 auto; border-radius: 999px; padding: 2px 7px; background: #EEF3F1; color: #52666B; font-size: 0.65rem; font-weight: 600; }}
.output-progress-track {{ height: 7px; background: #EAF0EE; border-radius: 999px; overflow: hidden; margin: 0.55rem 0 0.35rem; }}
.output-progress-fill {{ height: 100%; border-radius: 999px; }}
.output-progress-values {{ display: flex; justify-content: space-between; gap: 8px; color: #53666B; font-size: 0.72rem; }}
.output-progress-values strong {{ color: {NAVY}; white-space: nowrap; }}
.indicator-table-wrap {{ overflow-x: auto; margin: 0.5rem 0 1.4rem; background: #FFFFFF; border: 1px solid #DCE6E2; border-radius: 12px; box-shadow: 0 4px 14px rgba(24,58,70,0.055); }}
.indicator-table {{ width: 100%; min-width: 980px; border-collapse: collapse; }}
.indicator-table th {{ padding: 12px 14px; background: {NAVY}; color: #FFFFFF; font-size: 0.78rem; font-weight: 650; text-align: left; }}
.indicator-table td {{ padding: 12px 14px; border-bottom: 1px solid #E7EEEB; color: #24373D; font-size: 0.8rem; vertical-align: top; }}
.indicator-table tr:last-child td {{ border-bottom: 0; }}
.indicator-table tbody tr:nth-child(even) {{ background: #F8FBFA; }}
.indicator-table-output {{ font-weight: 700; white-space: nowrap; }}
.indicator-table-target, .indicator-table-achieved {{ white-space: nowrap; font-variant-numeric: tabular-nums; }}
.indicator-table-achieved {{ font-weight: 700; color: {NAVY}; }}
.indicator-table-progress {{ min-width: 120px; }}
.indicator-table-progress-label {{ display: flex; justify-content: space-between; gap: 8px; margin-bottom: 5px; font-size: 0.72rem; }}
.indicator-table-track {{ height: 7px; background: #EAF0EE; border-radius: 999px; overflow: hidden; }}
.indicator-table-fill {{ height: 100%; border-radius: 999px; }}
.indicator-table-details {{ min-width: 290px; max-width: 450px; color: #53666B !important; font-size: 0.74rem !important; line-height: 1.45; }}
@media (max-width: 760px) {{
    .block-container {{ padding: 2.5rem 1rem 2rem; }}
    div[data-testid="stRadio"] div[role="radiogroup"] {{ gap: 0.35rem; }}
    div[data-testid="stRadio"] div[role="radiogroup"] label {{ padding: 0.3rem 0.65rem; }}
    .output-progress-grid {{ grid-template-columns: 1fr; }}
}}
</style>
""", unsafe_allow_html=True)

st.sidebar.subheader("\U0001F4C2 Data upload")
uploaded = st.sidebar.file_uploader(
    "5W Excel workbook", type=["xlsx"],
    help="The dashboard reads the bundled UNICEF workbook unless a newer export is uploaded.",
)
DEFAULT_PATH = Path(__file__).with_name("Rasuwa - UNICEF_WASH_NEPAL_5Ws_Data_Entry.xlsx")


def load_manual_entries():
    return read_manual_entries(MANUAL_DATA_PATH)


def load_manual_gps_locations():
    if not MANUAL_GPS_DATA_PATH.exists():
        return pd.DataFrame(columns=["activity", "site_name", "palika", "district", "latitude", "longitude", "notes", "entry_date"])
    try:
        manual = pd.read_csv(MANUAL_GPS_DATA_PATH)
        if manual.empty:
            return pd.DataFrame(columns=["activity", "site_name", "palika", "district", "latitude", "longitude", "notes", "entry_date"])
        return manual
    except Exception:
        return pd.DataFrame(columns=["activity", "site_name", "palika", "district", "latitude", "longitude", "notes", "entry_date"])


@st.cache_data(show_spinner="Reading the 5W workbook…")
def get_data(workbook_bytes):
    return load_5w(BytesIO(workbook_bytes))

if uploaded is not None:
    workbook_source = uploaded
elif DEFAULT_PATH.is_file():
    workbook_source = DEFAULT_PATH
else:
    st.info(
        f"The bundled workbook {DEFAULT_PATH.name!r} is not present. Upload the current "
        "5W workbook using the sidebar; the dashboard will not silently load a differently "
        "named, potentially stale workbook."
    )
    st.stop()

try:
    workbook_bytes = workbook_source.getvalue() if uploaded is not None else workbook_source.read_bytes()
    df = get_data(workbook_bytes)
except Exception as exc:
    st.error(f"Could not read the 5W workbook: {exc}")
    st.stop()

try:
    manual_entries = load_manual_entries()
except RuntimeError as exc:
    st.error(str(exc))
    st.stop()

if not manual_entries.empty:
    allowed_manual_indicators = {item["indicator"] for item in MANUAL_INDICATORS}
    unexpected_indicators = sorted(
        set(manual_entries["indicator"].dropna()) - allowed_manual_indicators
    )
    if unexpected_indicators:
        st.error(
            "Saved manual entries contain indicators that are tracked in the Excel "
            f"workbook or are not supported: {', '.join(unexpected_indicators)}. "
            "Review the manual-entry CSV before continuing."
        )
        st.stop()
    manual_rows = manual_entries.copy()
    manual_rows["output"] = pd.to_numeric(manual_rows["output"], errors="coerce")
    manual_rows["activity_reached"] = pd.to_numeric(manual_rows["activity_reached"], errors="coerce")
    manual_rows["source_row"] = "manual"
    manual_rows["activity"] = manual_rows.get("activity", manual_rows["indicator"])
    manual_rows["subindicator"] = manual_rows.get("subindicator", manual_rows["activity"])
    manual_rows["district"] = manual_rows.get("district", "Rasuwa")
    manual_rows["municipality"] = manual_rows.get("municipality", "")
    manual_rows["status"] = manual_rows.get("status", "Completed")
    manual_rows["partner"] = manual_rows.get("partner", "UNICEF")
    df = pd.concat([df, manual_rows], ignore_index=True, sort=False)

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
unmapped = df[df["output"].isna() | df["indicator"].isna()]

st.sidebar.markdown("---")
st.sidebar.metric("\U0001F4CB 5W activity rows in scope", f"{len(df):,}", help="Includes populated activity rows for UNICEF and Chay-Ya Nepal.")
if excluded_partner_rows:
    st.sidebar.caption(f"{excluded_partner_rows} record(s) from other partners excluded.")
if len(unmapped):
    st.sidebar.warning(f"{len(unmapped)} activity row(s) are missing an output or programme-indicator mapping; review the Excel export.")
today = datetime.now().date()
if today < PROJECT_START:
    countdown_label = "Days until project starts"
    countdown_value = (PROJECT_START - today).days
elif today <= PROJECT_END:
    countdown_label = "Days until project ends"
    countdown_value = (PROJECT_END - today).days
else:
    countdown_label = "Days since project ended"
    countdown_value = (today - PROJECT_END).days
st.sidebar.metric(f"\U0001F4C5 {countdown_label}", f"{countdown_value:,}")
with st.sidebar.expander("Project & data details"):
    st.caption(f"Project period: {PROJECT_START.strftime('%d %b %Y')} – {PROJECT_END.strftime('%d %b %Y')}")
    st.caption(f"Dashboard refreshed: {datetime.now().strftime('%d %b %Y, %H:%M')}")
st.sidebar.download_button(
    "\U0001F4E5 Download monitoring pack",
    data=build_monitoring_workbook(df),
    file_name=f"rasuwa_wash_5w_monitoring_{datetime.now():%Y%m%d}.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    use_container_width=True,
)

st.markdown(
    f"<div class='project-title'>{PROJECT_TITLE}</div>",
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
    columns = ["Source 5W row"] + [FIELD_LABELS[col] for col in SOURCE_COLUMNS] + [
        "Mapped PD output", "Mapped PD indicator", FIELD_LABELS["subindicator"],
    ]
    if not full:
        columns = ["Source 5W row"] + [FIELD_LABELS[col] for col in DETAIL_COLUMNS] + [
            "Mapped PD output", "Mapped PD indicator",
        ]
    return table.reindex(columns=columns)


def palika_metric_table(frame):
    summary = build_palika_summary(frame).set_index("palika")
    summary.index = summary.index.str.replace(" Gaunpalika", "", regex=False)
    return summary


def render_activity_rollup(frame, key):
    activity_rollup = build_activity_rollup(frame)
    if activity_rollup.empty:
        st.info("No populated activity rows for this selection.")
        return
    columns = [
        "activity", "subindicator", "indicator", "activity_indicator",
        "activity_indicator_unit", "activity_rows", "target_rows_reported",
        "unit_target", "reached_rows_reported", "unit_reached", "completion_pct",
        "people_reached", "households_reached", "girls", "boys", "women", "men",
        "elderly_women", "elderly_men", "pwd", "demographic_total",
        "beneficiary_mismatch_rows",
    ]
    labels = {
        "activity": "Activity", "subindicator": "Sub-activity",
        "indicator": "Programme indicator", "activity_indicator": "Excel activity indicator",
        "activity_indicator_unit": "Target/reached unit", "activity_rows": "Rows",
        "target_rows_reported": "Rows with target", "unit_target": "Target total",
        "reached_rows_reported": "Rows with reached value", "unit_reached": "Reached total",
        "completion_pct": "Target progress (%)", "people_reached": "People reached (Excel total)",
        "households_reached": "Households reached", "demographic_total": "People in age/sex breakdown",
        "girls": "Girls (<18)", "boys": "Boys (<18)", "women": "Women (18+)",
        "men": "Men (18+)", "elderly_women": "Elderly women (60+)",
        "elderly_men": "Elderly men (60+)", "pwd": "People with disabilities",
        "beneficiary_mismatch_rows": "Rows with beneficiary mismatch",
    }
    st.dataframe(
        activity_rollup[columns].rename(columns=labels),
        width="stretch", hide_index=True, key=key,
    )


def render_palika_bar(frame, measure, chart_key):
    if measure == "People reached (row total)":
        values = palika_metric_table(frame)["people_reached"]
    elif measure == "Households reached (row total)":
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


st.title(PAGE_TITLES[page])

if page == "Overview":
    st.caption("Five programme outputs · ten targets · UNICEF 5W activity progress")
    st.markdown("### Target progress by output")
    output_cards = []
    for _, item in output_labels.iterrows():
        output_number = int(item["output"])
        output_indicators = indicator_summary[indicator_summary["output"] == output_number]
        indicator_cards = []
        for _, indicator in output_indicators.iterrows():
            target = float(indicator["target"])
            progress = float(indicator["progress"]) if pd.notna(indicator["progress"]) else 0.0
            pct = float(indicator["pct"]) if pd.notna(indicator["pct"]) else 0.0
            bar_pct = min(max(pct, 0.0), 100.0)
            remaining = max(target - progress, 0.0)
            if not indicator["tracked_in_5w"]:
                status = "Manual"
            elif pct >= 100:
                status = "Reached"
            elif progress > 0:
                status = "In progress"
            else:
                status = "Not started"
            indicator_cards.append(
                f'<div class="output-indicator">'
                f'<div class="output-indicator-heading"><span>{indicator["indicator"]}</span>'
                f'<span class="output-indicator-status">{status}</span></div>'
                f'<div class="output-progress-track"><div class="output-progress-fill" '
                f'style="width:{bar_pct:.1f}%;background:{OUTPUT_COLORS[output_number]};"></div></div>'
                f'<div class="output-progress-values"><span>{progress:,.0f} / {target:,.0f} '
                f'{indicator["unit"]}</span><strong>{pct:.1f}%</strong></div>'
                f'<div class="output-progress-values"><span>Remaining</span>'
                f'<span>{remaining:,.0f} {indicator["unit"]}</span></div></div>'
            )
        short_label = item["output_label"].split("\u2013", 1)[-1].strip()
        output_cards.append(
            f'<section class="output-progress-card" style="border-top-color:{OUTPUT_COLORS[output_number]}">'
            f'<div class="output-progress-title">Output {output_number}</div>'
            f'<div class="output-progress-subtitle">{short_label} · {len(output_indicators)} indicators</div>'
            f'{"".join(indicator_cards)}</section>'
        )
    st.markdown(
        f'<div class="output-progress-grid">{"".join(output_cards)}</div>',
        unsafe_allow_html=True,
    )

    st.markdown("### Indicator targets & progress")
    tracker_rows = []
    for _, indicator in indicator_summary.iterrows():
        output_number = int(indicator["output"])
        target = float(indicator["target"])
        progress = float(indicator["progress"]) if pd.notna(indicator["progress"]) else 0.0
        pct = float(indicator["pct"]) if pd.notna(indicator["pct"]) else 0.0
        bar_pct = min(max(pct, 0.0), 100.0)
        details = escape(str(indicator["progress_basis"]))
        if not details.strip():
            details = "No matching activity records in the current workbook."
        tracker_rows.append(
            f'<tr><td class="indicator-table-output" style="color:{OUTPUT_COLORS[output_number]}">'
            f'Output {output_number}</td>'
            f'<td>{escape(str(indicator["indicator"]))}</td>'
            f'<td class="indicator-table-target">{target:,.0f} {escape(str(indicator["unit"]))}</td>'
            f'<td class="indicator-table-achieved">{progress:,.0f} {escape(str(indicator["unit"]))}</td>'
            f'<td class="indicator-table-progress"><div class="indicator-table-progress-label">'
            f'<span>{pct:.1f}%</span><span>{max(target - progress, 0):,.0f} remaining</span></div>'
            f'<div class="indicator-table-track"><div class="indicator-table-fill" '
            f'style="width:{bar_pct:.1f}%;background:{OUTPUT_COLORS[output_number]}"></div></div></td>'
            f'<td class="indicator-table-details">{details}</td></tr>'
        )
    st.markdown(
        '<div class="indicator-table-wrap"><table class="indicator-table">'
        '<thead><tr><th>Output</th><th>Indicator</th><th>Target</th><th>Achieved</th>'
        '<th>Progress</th><th>Details</th></tr></thead>'
        f'<tbody>{"".join(tracker_rows)}</tbody></table></div>',
        unsafe_allow_html=True,
    )

    st.markdown("### Activity target progress")
    st.caption("Each bar is one 5W activity target. Targets are not added together, so different units remain separate.")
    target_outputs = sorted(INDICATORS_DF["output"].unique().tolist())
    available_target_outputs = sorted(
        build_activity_target_summary(df)["output"].dropna().astype(int).unique().tolist()
    )
    default_target_output = available_target_outputs[0] if available_target_outputs else target_outputs[0]
    selected_target_output = st.selectbox(
        "Programme output", target_outputs,
        index=target_outputs.index(default_target_output),
        format_func=lambda number: output_names[number], key="overview_target_output",
    )
    target_rows = build_activity_target_summary(df, selected_target_output)
    progress_rows = target_rows.dropna(subset=["activity_reached"]).copy()
    target_kpis = st.columns(3)
    target_kpis[0].metric("Activity targets reported", f"{len(target_rows):,}")
    target_kpis[1].metric("With progress reported", f"{len(progress_rows):,}")
    target_kpis[2].metric(
        "Targets reached", f"{int((progress_rows['activity_reached'] >= progress_rows['activity_target']).sum()):,}"
    )

    if len(progress_rows):
        target_chart = px.bar(
            progress_rows.sort_values("completion_pct"),
            x="completion_pct", y="target_label", orientation="h", color="status",
            color_discrete_map=STATUS_COLORS,
            hover_data={
                "activity_label": True, "activity": True, "municipality": True, "ward": True,
                "activity_target": True, "activity_reached": True, "activity_unit": True,
                "completion_pct": ":.1f", "status": True, "target_label": False,
            },
            labels={
                "completion_pct": "Activity target reached (%)", "target_label": "",
                "status": "Activity status", "activity_label": "5W indicator",
                "activity_target": "Target", "activity_reached": "Reached", "activity_unit": "Unit",
            },
        )
        target_chart.add_vline(x=100, line_dash="dot", line_color=NAVY, annotation_text="Target")
        target_chart.update_traces(texttemplate="%{x:.0f}%", textposition="outside", cliponaxis=False)
        target_chart.update_layout(
            height=max(300, 78 * len(progress_rows)), plot_bgcolor="white", paper_bgcolor="white",
            legend_title="", margin=dict(l=8, r=50, t=18, b=28),
        )
        st.plotly_chart(target_chart, width="stretch", key="overview_activity_target_chart")
    else:
        st.info("No activity targets are recorded for this output in the current 5W data.")

    if len(target_rows):
        target_table = target_rows[[
            "source_row", "activity_label", "activity", "municipality", "ward",
            "activity_target", "activity_reached", "activity_unit", "completion_pct", "status",
        ]].rename(columns={
            "source_row": "Source 5W row", "activity_label": "5W indicator", "activity": "Activity",
            "municipality": "Palika", "ward": "Ward", "activity_target": "Activity target",
            "activity_reached": "Activity reached", "activity_unit": "Unit",
            "completion_pct": "Progress (%)", "status": "Status",
        })
        st.dataframe(target_table, width="stretch", hide_index=True)
    unmapped_targets = build_activity_target_summary(
        df[df["output"].isna() | df["indicator"].isna()]
    )
    if len(unmapped_targets):
        st.warning(f"{len(unmapped_targets)} activity target row(s) are missing a programme mapping and need review.")

elif page == "Palika detail":
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
        "People reached (row total)", "Households reached (row total)", "Activity records",
        "People targeted (row total)", "Households targeted (row total)", "Relief items distributed",
    ]
    measure = st.selectbox("Compare Palikas by", measure_options, key="palika_measure")
    render_palika_bar(filtered, measure, "palika_metric_chart")
    if measure.endswith("row total"):
        st.caption("Values are summed as reported per 5W activity row and may include repeated reports.")

    st.markdown("### Output/activity progress for selected Palikas")
    render_activity_rollup(filtered, "palika_activity_rollup")

    st.markdown("### Activity register")
    st.dataframe(display_register(filtered), width="stretch", height=440, hide_index=True)
    with st.expander("Show every source 5W field"):
        st.dataframe(display_register(filtered, full=True, height=550), width="stretch", height=550, hide_index=True)

elif page == "Activities by output":
    st.caption("Unpack each output into its reported activity types, status, and reach.")
    default_output = active_output_numbers[0] if active_output_numbers else output_numbers[0]
    selected_output = st.selectbox(
        "Programme output", output_numbers, index=output_numbers.index(default_output),
        format_func=lambda number: output_names[number], key="activity_output",
    )
    output_frame = df[df["output"] == selected_output].copy()
    st.warning(
        "People and household reach are summed from the 5W rows and may overlap across activity "
        "types. Age/sex totals are shown separately; elderly and disability counts may overlap "
        "those groups and are not added to the demographic total."
    )
    activity_options = ["All activities"] + sorted(output_frame["activity"].dropna().unique().tolist())
    selected_activity = st.selectbox("Activity type", activity_options, key="activity_type")
    if selected_activity != "All activities":
        output_frame = output_frame[output_frame["activity"] == selected_activity]
    activity_statuses = sorted(output_frame["status"].dropna().unique().tolist())
    selected_activity_status = st.multiselect(
        "Activity status", activity_statuses, default=activity_statuses, key="activity_status",
    )
    output_frame = output_frame[output_frame["status"].isin(selected_activity_status)]

    reported_reach = build_palika_output_summary(output_frame)
    reported_reach = reported_reach[reported_reach["output"] == selected_output]["progress"].sum()
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Activity rows", f"{len(output_frame):,}")
    k2.metric("Palikas", f"{output_frame['municipality'].nunique():,}")
    k3.metric("People reached", f"{reported_reach:,.0f}", help="Sum of the people-reached values reported in the matching 5W rows.")
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
            st.caption("Activity bars and the KPI both sum the people-reached values reported in the matching 5W rows.")

    st.markdown("### Activity, sub-activity, target, and beneficiary totals")
    st.caption(
        "Targets and reached values stay in each Excel Activity Indicator unit. People and "
        "households are separate totals from the corresponding reported 5W columns; the "
        "demographic total is shown only as a cross-check."
    )
    render_activity_rollup(output_frame, "output_activity_rollup")

    st.markdown("### Matching 5W records")
    st.dataframe(display_register(output_frame), width="stretch", height=420, hide_index=True)
    with st.expander("Show every source 5W field"):
        st.dataframe(display_register(output_frame, full=True, height=550), width="stretch", height=550, hide_index=True)

elif page == "Manual activity entry":
    st.caption("This page is only for programme targets not recorded in the 5W Excel sheet: coordination meetings, needs-and-damage assessment missions, and community feedback mechanisms. Other activity targets and beneficiaries must come from the workbook.")
    form = st.form("manual_activity_form")
    with form:
        col1, col2, col3 = st.columns(3)
        indicator_name = col1.selectbox(
            "Indicator",
            [item["indicator"] for item in MANUAL_INDICATORS],
            key="manual_indicator",
        )
        partner_value = col2.selectbox("Partner", ["UNICEF", "Chay-Ya Nepal"], index=0)
        selected_output = next(item["output"] for item in MANUAL_INDICATORS if item["indicator"] == indicator_name)
        municipality = col3.selectbox("Palika", PALIKAS, index=0)
        c4, c5, c6 = st.columns(3)
        district = c4.text_input("District", value="Rasuwa")
        activity_value = c5.number_input("Recorded value", min_value=0, step=1, value=0)
        status = c6.selectbox("Status", ["Completed", "Ongoing"], index=0)
        notes = st.text_area("Notes", value="")
        submitted = st.form_submit_button("Save manual record")

    if submitted:
        indicator_row = next(item for item in MANUAL_INDICATORS if item["indicator"] == indicator_name)
        new_row = {
            "output": indicator_row["output"],
            "indicator": indicator_row["indicator"],
            "activity": indicator_row["indicator"],
            "subindicator": indicator_row["indicator"],
            "activity_indicator_unit": indicator_row["unit"],
            "partner": partner_value,
            "district": district,
            "municipality": municipality,
            "status": status,
            "activity_reached": float(activity_value),
            "notes": notes,
            "entry_date": datetime.now().strftime("%Y-%m-%d"),
            "lead_agency": "",
            "source_row": "manual",
        }
        try:
            save_manual_entry(new_row, MANUAL_DATA_PATH)
        except RuntimeError as exc:
            st.error(str(exc))
        else:
            st.success(f"Saved manual record for {indicator_name}.")
            st.rerun()

    st.markdown("### Saved manual records")
    saved_rows = load_manual_entries()
    if saved_rows.empty:
        st.info("No manual records saved yet. Add the missing activity values above and they will be included in the dashboard totals.")
    else:
        display = saved_rows.copy()
        display["output"] = display["output"].apply(lambda x: f"Output {int(float(x))}" if pd.notna(x) and str(x).strip() not in ("", "nan") else "")
        display.insert(0, "Record #", range(1, len(display) + 1))
        st.dataframe(display, width="stretch", hide_index=True)

        def manual_record_label(position):
            record = saved_rows.iloc[position]
            indicator = str(record.get("indicator", "Manual activity")).strip()
            reached = pd.to_numeric(record.get("activity_reached"), errors="coerce")
            reached_label = f"{reached:,.0f}" if pd.notna(reached) else "No value"
            entry_date = str(record.get("entry_date", "")).strip()
            return f"Record {position + 1} · {indicator} · {reached_label} · {entry_date}"

        delete_form = st.form("delete_manual_record_form")
        with delete_form:
            selected_manual_position = st.selectbox(
                "Choose a saved record to delete",
                range(len(saved_rows)),
                format_func=manual_record_label,
            )
            delete_submitted = st.form_submit_button("Delete selected record")

        if delete_submitted:
            try:
                delete_manual_entry(int(selected_manual_position), MANUAL_DATA_PATH)
            except (IndexError, RuntimeError) as exc:
                st.error(f"Could not delete the selected manual record: {exc}")
            else:
                st.success("Manual record deleted.")
                st.rerun()

elif page == "Beneficiary demographics":
    st.caption(
        "Reported sex and age-group reach by selected programme output and activity. "
        "Elderly and disability counts are shown separately to avoid double-counting overlapping groups."
    )
    demo_output_options = ["All outputs"] + output_numbers
    demo_output = st.selectbox(
        "Programme output", demo_output_options,
        format_func=lambda number: "All outputs" if number == "All outputs" else output_names[number],
        key="demo_output",
    )
    demographic_rows = df.copy()
    if demo_output != "All outputs":
        demographic_rows = demographic_rows[demographic_rows["output"] == demo_output]
    demo_activities = ["All activities"] + sorted(
        demographic_rows["activity"].dropna().unique().tolist()
    )
    demo_activity = st.selectbox("Activity", demo_activities, key="demo_activity")
    if demo_activity != "All activities":
        demographic_rows = demographic_rows[demographic_rows["activity"] == demo_activity]
    demo_subactivities = ["All sub-activities"] + sorted(
        demographic_rows["subindicator"].dropna().unique().tolist()
    )
    demo_subactivity = st.selectbox(
        "Sub-activity", demo_subactivities, key="demo_subactivity",
    )
    if demo_subactivity != "All sub-activities":
        demographic_rows = demographic_rows[demographic_rows["subindicator"] == demo_subactivity]
    demo_palikas = st.multiselect("Palika", PALIKAS, default=PALIKAS, key="demo_palikas")
    demo_statuses = sorted(demographic_rows["status"].dropna().unique().tolist())
    demo_selected_status = st.multiselect("Activity status", demo_statuses, default=demo_statuses, key="demo_status")
    demographic_rows = demographic_rows[
        demographic_rows["municipality"].isin(demo_palikas)
        & demographic_rows["status"].isin(demo_selected_status)
    ]
    demo_names = [palika.replace(" Gaunpalika", "") for palika in PALIKAS if palika in demo_palikas]
    demo = palika_metric_table(demographic_rows).reindex(demo_names)
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
    st.markdown("### Matching output/activity target and reach")
    render_activity_rollup(demographic_rows, "demographic_activity_rollup")

elif page == "Beneficiary explorer":
    st.caption("Filter by output, programme target, workbook activity, and sub-activity.")
    output_choices = ["All outputs"] + output_numbers
    chosen_output = st.selectbox(
        "Programme output", output_choices,
        format_func=lambda number: "All outputs" if number == "All outputs" else output_names[number],
        key="beneficiary_output",
    )
    beneficiary_rows = df.copy()
    if chosen_output != "All outputs":
        beneficiary_rows = beneficiary_rows[beneficiary_rows["output"] == chosen_output]
    indicator_choices = ["All indicators"] + sorted(beneficiary_rows["indicator"].dropna().unique().tolist())
    chosen_indicator = st.selectbox("Programme indicator", indicator_choices, key="beneficiary_indicator")
    if chosen_indicator != "All indicators":
        beneficiary_rows = beneficiary_rows[beneficiary_rows["indicator"] == chosen_indicator]
    activity_choices = ["All activities"] + sorted(
        beneficiary_rows["activity"].dropna().unique().tolist()
    )
    chosen_activity = st.selectbox("Activity", activity_choices, key="beneficiary_activity")
    if chosen_activity != "All activities":
        beneficiary_rows = beneficiary_rows[beneficiary_rows["activity"] == chosen_activity]
    subindicator_choices = ["All sub-indicators"] + sorted(beneficiary_rows["subindicator"].dropna().unique().tolist())
    chosen_subindicator = st.selectbox(
        "Activity sub-indicator", subindicator_choices, key="beneficiary_subindicator",
    )
    if chosen_subindicator != "All sub-indicators":
        beneficiary_rows = beneficiary_rows[beneficiary_rows["subindicator"] == chosen_subindicator]
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
    st.caption("Totals sum the people or household reach reported in the selected 5W rows.")
    st.dataframe(chart_data, width="stretch", hide_index=True)
    st.markdown("### Selected activity target/reached totals")
    render_activity_rollup(beneficiary_rows, "beneficiary_activity_rollup")

elif page == "Planning":
    st.caption(
        "All ten programme indicator targets are shown together. Activities with the lowest "
        "completion rate are prioritized first; percentages make targets with different units comparable."
    )
    planning_rows = indicator_summary.copy()
    planning_rows["pct"] = planning_rows["pct"].fillna(0)
    planning_rows["remaining"] = (planning_rows["target"] - planning_rows["progress"].fillna(0)).clip(lower=0)
    manual_indicator_names = {item["indicator"] for item in MANUAL_INDICATORS}
    manual_records = set(df.loc[df["source_row"].eq("manual"), "indicator"].dropna())
    planning_rows["tracking"] = planning_rows["indicator"].map(
        lambda indicator: (
            "Manual" if indicator in manual_records else "No manual update"
        ) if indicator in manual_indicator_names else "5W"
    )
    planning_rows["priority"] = planning_rows["pct"].map(
        lambda pct: "Achieved" if pct >= 100 else
        "Monitor" if pct >= 50 else
        "High" if pct >= 25 else "Urgent"
    )
    planning_rows = planning_rows.sort_values("pct", ascending=True, kind="stable").reset_index(drop=True)
    planning_rows.insert(0, "priority_rank", range(1, len(planning_rows) + 1))

    k1, k2, k3 = st.columns(3)
    k1.metric("Programme targets", f"{len(planning_rows)} / 10")
    k2.metric("With progress reported", f"{int((planning_rows['progress'].fillna(0) > 0).sum())} / 10")
    k3.metric("Indicators on target", f"{int((planning_rows['pct'] >= 100).sum())} / 10")

    planning_chart_data = planning_rows.copy()
    planning_chart_data["chart_pct"] = planning_chart_data["pct"].clip(lower=0, upper=100)
    priority_chart = px.bar(
        planning_chart_data,
        x="chart_pct",
        y="indicator",
        orientation="h",
        color="priority",
        color_discrete_map={
            "Urgent": "#B5473C", "High": "#D28B27",
            "Monitor": "#00AEEF", "Achieved": COMPLETED_GREEN,
        },
        custom_data=["progress", "target", "remaining", "unit", "pct", "tracking"],
        labels={"chart_pct": "Target completion (%)", "indicator": "", "priority": "Priority"},
    )
    priority_chart.add_vline(x=100, line_dash="dot", line_color=NAVY, annotation_text="Target")
    priority_chart.update_traces(
        text=planning_chart_data["pct"].map(lambda pct: f"{pct:.1f}%"),
        textposition="outside", cliponaxis=False,
        hovertemplate=(
            "%{y}<br>Progress: %{customdata[0]:,.0f} %{customdata[3]}"
            "<br>Target: %{customdata[1]:,.0f} %{customdata[3]}"
            "<br>Remaining: %{customdata[2]:,.0f} %{customdata[3]}"
            "<br>Completion: %{customdata[4]:.1f}%"
            "<br>Tracking: %{customdata[5]}<extra></extra>"
        ),
    )
    priority_chart.update_layout(
        height=520, xaxis=dict(range=[0, 115], title="Target completion (%)"),
        yaxis=dict(autorange="reversed"),
        plot_bgcolor="white", paper_bgcolor="white", legend_title="",
        margin=dict(l=8, r=40, t=20, b=30),
    )
    st.plotly_chart(priority_chart, width="stretch", key="priority_chart")

    st.markdown("### Ten-target activity board")
    priority_view = planning_rows[[
        "priority_rank", "output_label", "indicator", "target", "progress", "remaining", "pct", "unit", "tracking", "priority",
    ]].rename(columns={
        "priority_rank": "Priority rank", "output_label": "Programme output", "indicator": "Activity / indicator", "target": "Target",
        "progress": "Progress achieved", "remaining": "Remaining", "pct": "Completion (%)",
        "unit": "Unit", "tracking": "Tracking", "priority": "Priority",
    })
    st.dataframe(priority_view, width="stretch", hide_index=True)
    st.caption(
        "Priority is ranked by completion percentage (lowest first), not by raw remaining count, "
        "because the targets use different units. Manually tracked indicators without an entry "
        "are treated as zero progress and marked “No manual update”."
    )
    st.markdown("### Output-level reporting summary")
    st.caption("Average target completion is shown alongside, not added to, row-reported beneficiary totals.")
    planning_output_view = build_output_reporting_summary(df, indicator_summary)[[
        "output", "output_label", "avg_pct", "activity_rows",
        "activity_target_rows", "activity_reached_rows", "people_reached",
        "households_reached",
    ]].rename(columns={
        "output": "Output #", "output_label": "Programme output",
        "avg_pct": "Average indicator progress (%)", "activity_rows": "Activity rows",
        "activity_target_rows": "Rows with activity targets",
        "activity_reached_rows": "Rows with activity reached values",
        "people_reached": "People reached (row total)",
        "households_reached": "Households reached (row total)",
    })
    st.dataframe(planning_output_view, width="stretch", hide_index=True)

else:
    st.caption("Shared Google My Maps layer and the related UNICEF / Chay-Ya activity records.")
    if hasattr(st, "iframe"):
        st.iframe(MAP_EMBED_URL, height=560)
    else:
        st.components.v1.iframe(MAP_EMBED_URL, height=560, scrolling=True)
    st.link_button("Open in Google My Maps", MAP_EDIT_URL)
    st.info("Map pins are not automatically matched to 5W rows: the source 5W export has no GPS coordinates or shared site ID.")

    st.markdown("### Add manual GPS location by activity")
    gps_form = st.form("manual_gps_form")
    with gps_form:
        col1, col2, col3 = st.columns(3)
        activity_choice = col1.selectbox(
            "Activity",
            sorted(df["activity"].dropna().unique().tolist()),
            key="manual_gps_activity",
        )
        site_name = col2.text_input("Site / place name", value="")
        palika_choice = col3.selectbox("Palika", PALIKAS, index=0)
        c4, c5, c6 = st.columns(3)
        district_value = c4.text_input("District", value="Rasuwa")
        latitude = c5.number_input("Latitude", min_value=-90.0, max_value=90.0, value=28.0, step=0.0001, format="%.6f")
        longitude = c6.number_input("Longitude", min_value=-180.0, max_value=180.0, value=85.0, step=0.0001, format="%.6f")
        notes = st.text_area("Notes", value="")
        saved_gps = st.form_submit_button("Save GPS location")

    if saved_gps:
        if site_name.strip() == "":
            st.warning("Please enter a site or place name before saving the GPS location.")
        else:
            manual_locations = load_manual_gps_locations()
            record = {
                "activity": activity_choice,
                "site_name": site_name.strip(),
                "palika": palika_choice,
                "district": district_value.strip() or "Rasuwa",
                "latitude": float(latitude),
                "longitude": float(longitude),
                "notes": notes,
                "entry_date": datetime.now().strftime("%Y-%m-%d"),
            }
            if manual_locations.empty:
                saved = pd.DataFrame([record])
            else:
                saved = pd.concat([manual_locations, pd.DataFrame([record])], ignore_index=True)
            saved.to_csv(MANUAL_GPS_DATA_PATH, index=False)
            st.success("GPS location saved for this activity and site.")
            st.rerun()

    manual_locations = load_manual_gps_locations()
    if manual_locations.empty:
        st.info("No manual GPS locations saved yet. Add a site with coordinates here to track the activity locations manually.")
    else:
        location_table = manual_locations.copy()
        location_table["coordinates"] = location_table.apply(
            lambda row: f"{row['latitude']}, {row['longitude']}", axis=1
        )
        st.dataframe(
            location_table[["activity", "site_name", "palika", "district", "coordinates", "notes", "entry_date"]],
            width="stretch",
            hide_index=True,
        )

    map_output_options = ["All outputs"] + output_numbers
    map_output = st.selectbox(
        "Programme output", map_output_options,
        format_func=lambda number: "All outputs" if number == "All outputs" else output_names[number],
        key="map_output",
    )
    map_activities = df.copy()
    if map_output != "All outputs":
        map_activities = map_activities[map_activities["output"] == map_output]
    map_activity_options = ["All activities"] + sorted(
        map_activities["activity"].dropna().unique().tolist()
    )
    map_activity = st.selectbox("Activity", map_activity_options, key="map_activity")
    if map_activity != "All activities":
        map_activities = map_activities[map_activities["activity"] == map_activity]
    map_palikas = st.multiselect("Palika", PALIKAS, default=PALIKAS, key="map_palikas")
    map_statuses = sorted(df["status"].dropna().unique().tolist())
    map_selected_statuses = st.multiselect("Activity status", map_statuses, default=map_statuses, key="map_statuses")
    map_rows = map_activities[
        map_activities["municipality"].isin(map_palikas)
        & map_activities["status"].isin(map_selected_statuses)
    ]
    st.markdown("### Selected output/activity totals")
    render_activity_rollup(map_rows, "map_activity_rollup")
    st.markdown("### Related 5W register")
    st.dataframe(display_register(map_rows), width="stretch", height=420, hide_index=True)
    with st.expander("Show every source 5W field"):
        st.dataframe(display_register(map_rows, full=True, height=550), width="stretch", height=550, hide_index=True)
