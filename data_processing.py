"""
Data processing layer for the Rasuwa WASH Dashboard.
Reads the UNICEF 5W export and the Chay-Ya monitoring matrix, maps every
5W activity row to one of the 5 PD Outputs / 10 indicators, and produces
clean, aggregated tables for the Streamlit app to display.
"""
from io import BytesIO

import pandas as pd
import numpy as np
import openpyxl

# ----------------------------------------------------------------------
# 1. Fixed reference: the 5 Outputs / 10 Indicators and their PD targets.
#    Source: Chay-Ya Monitoring Matrix, "WASH Response_Daily_Chaya" sheet.
# ----------------------------------------------------------------------
INDICATORS = [
    {"output": 1, "output_label": "Output 1 (W1) \u2013 Leadership & Coordination",
     "indicator": "Cluster coordination meetings (district & Palika)", "unit": "Meetings", "target": 4, "tracked_in_5w": False},
    {"output": 1, "output_label": "Output 1 (W1) \u2013 Leadership & Coordination",
     "indicator": "Field missions for needs & damage assessment", "unit": "Visits", "target": 4, "tracked_in_5w": False},
    {"output": 2, "output_label": "Output 2 (W2) \u2013 Water Supply",
     "indicator": "People accessing sufficient, safe water", "unit": "People", "target": 8000, "tracked_in_5w": True},
    {"output": 2, "output_label": "Output 2 (W2) \u2013 Water Supply",
     "indicator": "Water quality monitoring rounds (per ward)", "unit": "Events", "target": 5, "tracked_in_5w": True},
    {"output": 3, "output_label": "Output 3 (W3) \u2013 Sanitation",
     "indicator": "People accessing appropriate sanitation", "unit": "People", "target": 10600, "tracked_in_5w": True},
    {"output": 3, "output_label": "Output 3 (W3) \u2013 Sanitation",
     "indicator": "Women & girls reached with MHM services", "unit": "People", "target": 2120, "tracked_in_5w": True},
    {"output": 4, "output_label": "Output 4 (W4) \u2013 WASH in Schools & Health Facilities",
     "indicator": "Children using safe WASH facilities in learning spaces", "unit": "Children", "target": 3180, "tracked_in_5w": True},
    {"output": 5, "output_label": "Output 5 (W6) \u2013 Hygiene Promotion & Community Engagement",
     "indicator": "People reached with hygiene promotion", "unit": "People", "target": 10600, "tracked_in_5w": True},
    {"output": 5, "output_label": "Output 5 (W6) \u2013 Hygiene Promotion & Community Engagement",
     "indicator": "Functioning community feedback mechanisms", "unit": "Mechanisms", "target": 5, "tracked_in_5w": False},
    {"output": 5, "output_label": "Output 5 (W6) \u2013 Hygiene Promotion & Community Engagement",
     "indicator": "People reached with critical WASH supplies", "unit": "People", "target": 4250, "tracked_in_5w": True},
]
INDICATORS_DF = pd.DataFrame(INDICATORS)

OUTPUT_COLORS = {1: "#64748B", 2: "#1CABE2", 3: "#159488", 4: "#7C5CBF", 5: "#E1922E"}
PALIKAS = ["Gosaikunda Gaunpalika", "Uttargaya Gaunpalika", "Kalika Gaunpalika", "Aamachhodingmo Gaunpalika"]

# ----------------------------------------------------------------------
# 2. Activity -> (Output, Indicator) mapping.
#    Location-based override (school/CFS/health facility => Output 4)
#    takes priority over the activity-type mapping below.
# ----------------------------------------------------------------------
ACTIVITY_MAP = {
    # Output 2 - Water Supply (infrastructure & bulk water)
    "Emergency water provision": (2, "People accessing sufficient, safe water"),
    "Community water storage": (2, "People accessing sufficient, safe water"),
    "Water treatment": (2, "People accessing sufficient, safe water"),
    "Water-quality monitoring": (2, "Water quality monitoring rounds (per ward)"),
    "Water supply system/source": (2, "People accessing sufficient, safe water"),
    "Water system operation & maintenance support": (2, "People accessing sufficient, safe water"),
    "Rainwater harvesting system": (2, "People accessing sufficient, safe water"),
    "Recharge pond construction / rehabilitation": (2, "People accessing sufficient, safe water"),
    "Groundwater recharge": (2, "People accessing sufficient, safe water"),
    "Water source / catchment protection": (2, "People accessing sufficient, safe water"),
    # Output 3 - Sanitation
    "Emergency sanitation": (3, "People accessing appropriate sanitation"),
    "Sanitation facility": (3, "People accessing appropriate sanitation"),
    "Handwashing facility": (3, "People accessing appropriate sanitation"),
    "Bathing facility": (3, "People accessing appropriate sanitation"),
    "Desludging / faecal sludge management": (3, "People accessing appropriate sanitation"),
    "Solid waste collection and removal": (3, "People accessing appropriate sanitation"),
    "Solid waste disposal support": (3, "People accessing appropriate sanitation"),
    "Drainage cleaning / repair": (3, "People accessing appropriate sanitation"),
    "Environmental cleaning / disinfection": (3, "People accessing appropriate sanitation"),
    "Community clean-up / debris removal": (3, "People accessing appropriate sanitation"),
    "Vector control": (3, "People accessing appropriate sanitation"),
    # Output 5 - Hygiene promotion & supplies (household-level NFI + promotion)
    "Household water treatment": (5, "People reached with critical WASH supplies"),
    "Household water storage": (5, "People reached with critical WASH supplies"),
    "Hygiene supplies": (5, "People reached with critical WASH supplies"),
    "Hygiene promotion": (5, "People reached with hygiene promotion"),
    "WASH communication materials": (5, "People reached with hygiene promotion"),
    "Other WASH activity": None,  # left unmapped on purpose - needs manual review
}
# These two indicators are fed by several different "item" activities (different hygiene/
# NFI items, different IEC material types) that are commonly logged as separate rows for
# the SAME underlying distribution round at the SAME site, repeating that round's
# demographic figures on every row. Summing across those rows would count the same people
# once per item. Both are de-duplicated the same way: see build_indicator_summary.
DEDUP_INDICATORS = {"People reached with critical WASH supplies", "People reached with hygiene promotion"}
SCHOOL_KEYWORDS = ["school", "hostel", "cfs", "child friendly", "health facility", "health post", "hcf", "learning"]


def _parent_category(activity_text):
    """The standardized Activity string is 'Parent Category - Sub-activity'. Must be split
    the exact same way the reference list's own 'activity' field is split, not matched
    against its separate 'parent_activity' label, which uses different wording."""
    if not activity_text:
        return None
    return str(activity_text).split(" - ")[0].strip()


def classify_row(activity, location_type, holding_centre, type_specific_location):
    """Returns (output_number, indicator_label) for one 5W row, or (None, None) if unmappable."""
    loc_text = " ".join(str(x) for x in [location_type, holding_centre, type_specific_location] if x and str(x) != "nan").lower()
    is_school_type_site = any(k in loc_text for k in SCHOOL_KEYWORDS)

    parent = _parent_category(activity)
    base = ACTIVITY_MAP.get(parent)

    if is_school_type_site and base is not None:
        return 4, "Children using safe WASH facilities in learning spaces"
    if base is None:
        return None, None
    return base


# ----------------------------------------------------------------------
# 3. Load the UNICEF 5W workbook
# ----------------------------------------------------------------------
FIVEW_COLUMNS = {
    "IMPLEMENTING PARTNER": "partner", "DISTRICT": "district", "MUNICIPALITY": "municipality", "WARD": "ward",
    "HOLDING CENTRE / DISPLACEMENT SITE": "holding_centre", "TYPE SPECIFIC LOCATION": "type_specific_location",
    "LOCATION TYPE": "location_type", "ACTIVITY ": "activity", "ACTIVITY DESCRIPTION ": "activity_description",
    "RESPONSE MODALITY ": "modality", "ACTIVITY TARGET": "activity_target", "ACTIVITY REACHED": "activity_reached",
    "HOUSEHOLDS TARGETED": "hh_targeted", "PEOPLE TARGETED (Individuals)": "people_targeted",
    "HOUSEHOLDS REACHED": "hh_reached", "TOTAL NUMBER OF BENEFICIARIES REACHED (people/individuals)": "people_reached",
    "GIRLS (< 18 yrs)": "girls", "BOYS (< 18 yrs)": "boys", "WOMEN (18+ yrs)": "women", "MEN  (18+ yrs)": "men",
    "ELDERLY WOMEN (60 plus)": "elderly_women", "ELDERLY MEN (60 plus)": "elderly_men",
    "PEOPLE WITH DISABILITIES": "pwd", "ACTIVITY STATUS ": "status",
    " ACTIVITY START DATE": "start_date", "ACTIVITY END DATE": "end_date", "NOTES": "notes",
}


def load_5w(path, sheet_name="5W_Data_Entry", header_row=6):
    wb = openpyxl.load_workbook(path, data_only=True)
    ws = wb[sheet_name]
    headers = [ws.cell(row=header_row, column=c).value for c in range(1, ws.max_column + 1)]
    rows = []
    for r in range(header_row + 1, ws.max_row + 1):
        vals = [ws.cell(row=r, column=c).value for c in range(1, len(headers) + 1)]
        if all(v in (None, "") for v in vals):
            continue
        rows.append(dict(zip(headers, vals)))
    df = pd.DataFrame(rows)
    df = df.rename(columns={k: v for k, v in FIVEW_COLUMNS.items() if k in df.columns})
    keep = list(FIVEW_COLUMNS.values())
    for col in keep:
        if col not in df.columns:
            df[col] = np.nan
    df = df[["partner", "district", "municipality", "ward"] + [c for c in keep if c not in ("partner", "district", "municipality", "ward")]]
    for c in ["people_reached", "hh_reached", "girls", "boys", "women", "men", "elderly_women", "elderly_men",
              "pwd", "people_targeted", "hh_targeted", "activity_target", "activity_reached"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["municipality"] = df["municipality"].astype(str).str.strip()
    # Source sheet mixes real dates, typed text, and blanks in the same column - coerce to a
    # single consistent type so later display/serialization doesn't choke on the mix.
    for c in ["start_date", "end_date"]:
        # dayfirst=True: Nepal data is DD/MM/YYYY: without this, ambiguous dates like
        # 03/10/2026 silently get misread as March instead of 3 October.
        df[c] = pd.to_datetime(df[c], errors="coerce", dayfirst=True).dt.strftime("%d-%b-%Y")
        df[c] = df[c].fillna("")
    out_ind = df.apply(lambda row: classify_row(row["activity"], row["location_type"], row["holding_centre"], row["type_specific_location"]), axis=1)
    df["output"] = out_ind.apply(lambda t: t[0])
    df["indicator"] = out_ind.apply(lambda t: t[1])
    return df


def progress_value(row):
    """Best available 'reached' figure for a row: people reached, else activity reached (service/infra), else 0."""
    if pd.notna(row["people_reached"]) and row["people_reached"] > 0:
        return row["people_reached"]
    if pd.notna(row["activity_reached"]) and row["activity_reached"] > 0 and row["indicator"] == "Water quality monitoring rounds (per ward)":
        return row["activity_reached"]
    return 0


def is_dedup_row(indicator):
    return indicator in DEDUP_INDICATORS


def build_indicator_summary(df):
    """Sums progress per indicator normally, EXCEPT for the two indicators in
    DEDUP_INDICATORS, where multiple item-type rows commonly share one real distribution
    round and repeat its figures. For those, within each municipality we take the single
    largest reported reach among that area's rows for the indicator (a conservative "at
    least this many unique people were reached" figure), then add those per-area figures
    together, rather than summing every item row separately."""
    df = df.copy()
    df["progress"] = df.apply(progress_value, axis=1)
    df["dedup"] = df["indicator"].apply(is_dedup_row)

    dedup_totals = {}
    for ind in DEDUP_INDICATORS:
        mask = df["dedup"] & (df["indicator"] == ind)
        dedup_totals[ind] = df[mask].groupby("municipality")["progress"].max().sum() if mask.any() else 0

    normal = df[~df["dedup"]]
    agg = normal.groupby("indicator", dropna=True)["progress"].sum().reset_index()

    summary = INDICATORS_DF.merge(agg, on="indicator", how="left")
    summary["progress"] = summary["progress"].fillna(0)
    for ind, val in dedup_totals.items():
        summary.loc[summary["indicator"] == ind, "progress"] = val
    summary.loc[~summary["tracked_in_5w"], "progress"] = np.nan
    summary["pct"] = (summary["progress"] / summary["target"] * 100).round(1)
    return summary


def build_output_summary(indicator_summary):
    rows = []
    for out_num in sorted(indicator_summary["output"].unique()):
        sub = indicator_summary[indicator_summary["output"] == out_num]
        tracked = sub[sub["tracked_in_5w"]]
        pct = tracked["pct"].mean() if len(tracked) else np.nan
        rows.append({
            "output": out_num, "output_label": sub["output_label"].iloc[0],
            "n_indicators": len(sub), "avg_pct": pct,
            "color": OUTPUT_COLORS[out_num],
        })
    return pd.DataFrame(rows)


def build_palika_output_summary(df):
    """Aggregate reach by Palika and Output using the indicator de-duplication rules."""
    working = df.copy()
    working["progress"] = working.apply(progress_value, axis=1)
    normal = working[~working["indicator"].isin(DEDUP_INDICATORS)]
    normal_totals = normal.groupby(["municipality", "output"], dropna=True)["progress"].sum().reset_index()

    dedup = working[working["indicator"].isin(DEDUP_INDICATORS)]
    if len(dedup):
        output_by_indicator = INDICATORS_DF.set_index("indicator")["output"]
        dedup_totals = dedup.groupby(["municipality", "indicator"], dropna=True)["progress"].max().reset_index()
        dedup_totals["output"] = dedup_totals["indicator"].map(output_by_indicator)
        dedup_totals = dedup_totals.groupby(["municipality", "output"], dropna=True)["progress"].sum().reset_index()
        normal_totals = pd.concat([normal_totals, dedup_totals], ignore_index=True)

    return normal_totals.groupby(["municipality", "output"], as_index=False)["progress"].sum()


DEMO_COLS = ["progress", "hh_reached", "girls", "boys", "women", "men", "elderly_women", "elderly_men", "pwd"]


def _dedup_group_totals(group):
    """Within one (Palika x dedup-indicator) group: the source data often repeats the SAME
    demographic figures across every item-row from one distribution round (different
    hygiene/NFI items, different IEC material types, all logged with identical
    girls/boys/women/men for that visit), while 'people reached' varies per item based on
    stock. Taking each column's max independently would mix figures from different rows
    together inconsistently. Instead we pick the ONE row with the largest people-reached
    figure and take ALL of its numbers together, so the demographic split always
    corresponds to a single real reported event rather than a Frankenstein of several."""
    if not len(group) or group["progress"].max() == 0:
        return {c: 0 for c in DEMO_COLS}
    best_idx = group["progress"].idxmax()
    return {c: (group.loc[best_idx, c] if pd.notna(group.loc[best_idx, c]) else 0) for c in DEMO_COLS}


def build_palika_summary(df):
    """Per-Palika totals. Rows feeding a DEDUP_INDICATORS indicator are de-duplicated by
    keeping only the single largest reported round's full set of figures per indicator
    (see _dedup_group_totals), so girls/boys/women/men stay internally consistent with
    each other and with the headline people-reached number, instead of summing or mixing
    values across repeated item rows. Everything else sums normally."""
    df = df.copy()
    df["progress"] = df.apply(progress_value, axis=1)
    df["dedup"] = df["indicator"].apply(is_dedup_row)
    df["municipality"] = df["municipality"].astype(str).str.strip().replace({"nan": np.nan})
    rows = []
    for palika in PALIKAS:
        sub = df[df["municipality"] == palika]
        row = {"palika": palika, "activities": len(sub)}
        for c in DEMO_COLS:
            row[c] = 0
        for ind in DEDUP_INDICATORS:
            group = sub[(sub["dedup"]) & (sub["indicator"] == ind)]
            totals = _dedup_group_totals(group)
            for c in DEMO_COLS:
                row[c] += totals[c]
        normal = sub[~sub["dedup"]]
        for c in DEMO_COLS:
            row[c] += normal[c].fillna(0).sum()
        row["people_reached"] = row.pop("progress")
        row["households_reached"] = row.pop("hh_reached")
        rows.append(row)
    return pd.DataFrame(rows)


def build_monitoring_workbook(df):
    """Create a formatted Excel monitoring pack from the loaded UNICEF 5W records."""
    indicator_summary = build_indicator_summary(df).copy()
    indicator_summary["gap_to_target"] = (
        indicator_summary["target"] - indicator_summary["progress"]
    ).clip(lower=0)
    indicator_summary["tracking_status"] = np.select(
        [
            ~indicator_summary["tracked_in_5w"],
            indicator_summary["progress"].fillna(0) >= indicator_summary["target"],
            indicator_summary["progress"].fillna(0) > 0,
        ],
        ["Manual tracking", "Target reached", "In progress"],
        default="Not started",
    )
    indicator_columns = {
        "output_label": "Output", "indicator": "Indicator", "unit": "Unit",
        "target": "Target", "progress": "Progress", "gap_to_target": "Remaining",
        "pct": "Progress (%)", "tracked_in_5w": "Tracked in 5W",
        "tracking_status": "Tracking status",
    }
    indicator_tracker = indicator_summary[list(indicator_columns)].rename(columns=indicator_columns)

    palika_columns = {
        "palika": "Palika", "activities": "Activity rows", "people_reached": "People reached",
        "households_reached": "Households reached", "girls": "Girls (<18)", "boys": "Boys (<18)",
        "women": "Women (18+)", "men": "Men (18+)", "elderly_women": "Elderly women (60+)",
        "elderly_men": "Elderly men (60+)", "pwd": "People with disabilities",
    }
    palika_tracker = build_palika_summary(df)[list(palika_columns)].rename(columns=palika_columns)

    register = df.copy()
    register["record_progress"] = register.apply(progress_value, axis=1)
    register["output"] = register["output"].map(lambda value: f"Output {int(value)}" if pd.notna(value) else "Unmapped")
    register = register.rename(columns={
        "partner": "Implementing partner", "district": "District", "municipality": "Palika",
        "ward": "Ward", "holding_centre": "Holding centre / displacement site",
        "type_specific_location": "Specific location", "location_type": "Location type",
        "activity": "Activity", "activity_description": "Activity description", "modality": "Modality",
        "activity_target": "Activity target", "activity_reached": "Activity reached",
        "hh_targeted": "Households targeted", "people_targeted": "People targeted",
        "hh_reached": "Households reached", "people_reached": "People reached",
        "record_progress": "Mapped indicator progress", "girls": "Girls (<18)", "boys": "Boys (<18)",
        "women": "Women (18+)", "men": "Men (18+)", "elderly_women": "Elderly women (60+)",
        "elderly_men": "Elderly men (60+)", "pwd": "People with disabilities", "status": "Activity status",
        "start_date": "Start date", "end_date": "End date", "notes": "Notes",
        "output": "Mapped output", "indicator": "Mapped indicator",
    })

    quality_rows = []
    for source_column, label in [
        ("ward", "Ward"), ("activity_description", "Activity description"),
        ("people_targeted", "People targeted"), ("people_reached", "People reached"),
        ("hh_targeted", "Households targeted"), ("hh_reached", "Households reached"),
        ("start_date", "Start date"), ("end_date", "End date"),
    ]:
        values = df[source_column]
        missing = values.isna() | values.astype(str).str.strip().eq("")
        quality_rows.append({
            "Field": label, "Records missing": int(missing.sum()),
            "Records populated": int((~missing).sum()), "Completeness (%)": round((~missing).mean() * 100, 1),
        })
    quality_rows.append({
        "Field": "Unmapped activity/output", "Records missing": int(df["output"].isna().sum()),
        "Records populated": int(df["output"].notna().sum()),
        "Completeness (%)": round(df["output"].notna().mean() * 100, 1),
    })
    quality = pd.DataFrame(quality_rows)
    unmapped = df[df["output"].isna()][["partner", "municipality", "ward", "activity", "activity_description", "status"]].rename(columns={
        "partner": "Implementing partner", "municipality": "Palika", "ward": "Ward",
        "activity": "Activity", "activity_description": "Activity description", "status": "Activity status",
    })

    sheets = {
        "Indicator Tracker": indicator_tracker,
        "Palika Tracker": palika_tracker,
        "5W Activity Register": register,
        "Data Quality": quality,
        "Unmapped Activities": unmapped,
    }
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        for sheet_name, table in sheets.items():
            table.to_excel(writer, sheet_name=sheet_name, index=False)
        workbook = writer.book
        header_fill = openpyxl.styles.PatternFill("solid", fgColor="0D3B54")
        for sheet_name, table in sheets.items():
            worksheet = workbook[sheet_name]
            worksheet.freeze_panes = "A2"
            worksheet.auto_filter.ref = worksheet.dimensions
            worksheet.row_dimensions[1].height = 30
            for cell in worksheet[1]:
                cell.fill = header_fill
                cell.font = openpyxl.styles.Font(color="FFFFFF", bold=True)
                cell.alignment = openpyxl.styles.Alignment(wrap_text=True, vertical="center")
            for column_cells in worksheet.columns:
                column_letter = column_cells[0].column_letter
                values = [len(str(cell.value)) for cell in column_cells if cell.value is not None]
                worksheet.column_dimensions[column_letter].width = min(max(max(values, default=10) + 2, 12), 42)
            if sheet_name == "Indicator Tracker":
                for row in range(2, worksheet.max_row + 1):
                    worksheet.cell(row, 7).number_format = '0.0"%"'
                worksheet.conditional_formatting.add(
                    f"G2:G{worksheet.max_row}",
                    openpyxl.formatting.rule.DataBarRule(start_type="num", start_value=0, end_type="num", end_value=100, color="1CABE2"),
                )
            elif sheet_name == "Data Quality":
                for row in range(2, worksheet.max_row + 1):
                    worksheet.cell(row, 4).number_format = '0.0"%"'

    return output.getvalue()


if __name__ == "__main__":
    df = load_5w("Rasuwa_-_UNICEF_WASH_NEPAL_5Ws_Data_Entry.xlsx")
    print(f"Loaded {len(df)} activity rows")
    print("\nUnmapped activities (need manual review):")
    print(df[df["output"].isna()]["activity"].value_counts())

    print("\n=== Indicator summary ===")
    ind = build_indicator_summary(df)
    print(ind[["output", "indicator", "target", "progress", "pct", "tracked_in_5w"]].to_string())

    print("\n=== Output summary ===")
    print(build_output_summary(ind).to_string())

    print("\n=== Palika summary ===")
    print(build_palika_summary(df).to_string())
