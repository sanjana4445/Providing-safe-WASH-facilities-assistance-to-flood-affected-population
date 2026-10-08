"""
Data processing layer for the Rasuwa WASH Dashboard.
Reads the UNICEF 5W export and the Chay-Ya monitoring matrix, maps every
5W activity row to one of the 5 PD Outputs / 10 indicators, and produces
clean, aggregated tables for the Streamlit app to display.
"""
from io import BytesIO
import re

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
INDICATOR_OUTPUTS = INDICATORS_DF.set_index("indicator")["output"].to_dict()

OUTPUT_COLORS = {
    1: "#58727F", 2: "#00AEEF", 3: "#D28B27", 4: "#E4775A", 5: "#26734D",
}
PALIKAS = ["Gosaikunda Gaunpalika", "Uttargaya Gaunpalika", "Kalika Gaunpalika", "Aamachhodingmo Gaunpalika"]
_PALIKA_SUFFIXES = {"gaunpalika", "gaupalika", "gaun", "gau", "palika", "rural", "municipality"}
_PALIKA_KEYS = {
    "".join(word for word in palika.casefold().split() if word not in _PALIKA_SUFFIXES): palika
    for palika in PALIKAS
}


def normalize_palika_name(value):
    """Map common municipality-name variants to the dashboard's canonical labels."""
    if pd.isna(value):
        return np.nan

    name = re.sub(r"[^a-z0-9]+", " ", str(value).casefold()).strip()
    words = [word for word in name.split() if word not in _PALIKA_SUFFIXES]
    key = "".join(words)
    return _PALIKA_KEYS.get(key, str(value).strip())

# ----------------------------------------------------------------------
# 2. Activity Indicator dropdown -> one of the fixed Programme Document targets.
#    The dropdown labels come from each uploaded workbook; unmatched values remain
#    unmapped rather than being guessed.
# ----------------------------------------------------------------------
WATER_QUALITY_INDICATOR = "Water quality monitoring rounds (per ward)"
MANUAL_TRACKED_INDICATORS = {
    "Cluster coordination meetings (district & Palika)",
    "Field missions for needs & damage assessment",
    "Functioning community feedback mechanisms",
}
SCHOOL_KEYWORDS = ["school", "hostel", "cfs", "child friendly", "health facility", "health post", "hcf", "learning"]
ACTIVITY_TAXONOMY_SHEET = "Activity_Indicator"


def _normalized_text(value):
    if pd.isna(value):
        return ""
    return re.sub(r"[^a-z0-9]+", " ", str(value).casefold()).strip()


def load_activity_taxonomy(workbook):
    """Read Activity dropdown values and their workbook-defined subsectors."""
    if ACTIVITY_TAXONOMY_SHEET not in workbook.sheetnames:
        raise ValueError(f"Workbook is missing the {ACTIVITY_TAXONOMY_SHEET!r} taxonomy sheet.")

    worksheet = workbook[ACTIVITY_TAXONOMY_SHEET]
    taxonomy = {}
    for row in worksheet.iter_rows(min_row=4, values_only=True):
        if len(row) < 3 or not row[2]:
            continue
        activity = str(row[2]).strip()
        taxonomy[_normalized_text(activity)] = {
            "activity": activity,
            "cluster": row[0],
            "subsector": row[1],
            "sub_activity": row[3],
        }
    if not taxonomy:
        raise ValueError(f"The {ACTIVITY_TAXONOMY_SHEET!r} taxonomy sheet has no activity values.")
    return taxonomy


def split_activity(activity):
    """Return the activity dropdown's parent category and sub-activity."""
    if pd.isna(activity) or not str(activity).strip():
        return None, None
    text = str(activity).strip()
    parent, separator, sub_activity = text.partition(" - ")
    return parent.strip(), sub_activity.strip() if separator else text


def map_activity_indicator(activity_indicator, unit):
    """Map the 5W Activity Indicator dropdown to a programme indicator."""
    if pd.isna(activity_indicator):
        return None

    text = re.sub(r"[^a-z0-9]+", " ", str(activity_indicator).casefold()).strip()
    if not text:
        return None
    if "mhm" in text or "dignity kit" in text:
        return "Women & girls reached with MHM services"
    if "water quality" in text or "water systems sources tested" in text or "water systems sources monitored" in text:
        normalized_unit = str(unit).casefold()
        return WATER_QUALITY_INDICATOR if "event" in normalized_unit else None
    if "water treatment" in text or "water storage" in text:
        return "People accessing sufficient, safe water"
    if "water system" in text or "water source" in text:
        return None
    if "hygiene kits" in text or "hygiene items" in text or "hygiene packages" in text:
        return "People reached with critical WASH supplies"
    if "communication materials" in text:
        return "People reached with hygiene promotion"
    if "hygiene promotion" in text or "promotion sessions" in text or "promotion activities" in text:
        return "People reached with hygiene promotion"
    if any(term in text for term in ("cholera prevention", "food hygiene")) and (
        "session" in text or "activity" in text
    ):
        return "People reached with hygiene promotion"
    if "recharge pond" in text:
        return "People accessing sufficient, safe water"
    if "water" in text:
        return "People accessing sufficient, safe water"
    if any(term in text for term in (
        "sanitation", "toilet", "latrine", "handwashing", "bathing",
        "desludged", "faecal sludge", "solid waste", "waste disposal",
        "drainage", "environmental cleaning", "vector control",
        "clean up", "debris removal", "spraying", "larval control",
    )):
        return "People accessing appropriate sanitation"
    return None


def output_for_activity(activity, taxonomy):
    """Map a workbook Activity dropdown value to its programme output."""
    entry = taxonomy.get(_normalized_text(activity))
    if entry is None:
        return None, None, None

    subsector = _normalized_text(entry["subsector"])
    activity_text = _normalized_text(f"{entry['activity']} {entry['sub_activity'] or ''}")
    if "water" in subsector:
        output = 2
    elif "sanitation" in subsector:
        output = 3
    elif "hygiene" in subsector:
        output = 3 if any(term in activity_text for term in ("mhm", "dignity")) else 5
    else:
        output = None

    sub_activity = entry["sub_activity"]
    if sub_activity and str(sub_activity).strip():
        subindicator = str(sub_activity).strip()
    else:
        _, subindicator = split_activity(activity)
    return output, subindicator, entry


def classify_row(activity, activity_indicator, activity_indicator_unit, location_type, holding_centre, type_specific_location, activity_taxonomy=None):
    """Map workbook taxonomy values and activity-indicator values to a PD output and indicator."""
    loc_text = " ".join(str(x) for x in [location_type, holding_centre, type_specific_location] if x and str(x) != "nan").lower()
    is_school_type_site = any(k in loc_text for k in SCHOOL_KEYWORDS)

    indicator = map_activity_indicator(activity_indicator, activity_indicator_unit)
    if activity_taxonomy is None:
        _, subindicator = split_activity(activity)
        output = INDICATOR_OUTPUTS.get(indicator)
    else:
        output, subindicator, entry = output_for_activity(activity, activity_taxonomy)
        if entry is None:
            return None, None, split_activity(activity)[1]
    if not subindicator:
        return output, None, subindicator
    if indicator is None:
        return output, None, subindicator
    if is_school_type_site and indicator in {
        "People accessing sufficient, safe water",
        "People accessing appropriate sanitation",
    }:
        return 4, "Children using safe WASH facilities in learning spaces", subindicator
    if output != INDICATOR_OUTPUTS[indicator]:
        return output, None, subindicator
    return output, indicator, subindicator


# ----------------------------------------------------------------------
# 3. Load the UNICEF 5W workbook
# ----------------------------------------------------------------------
FIVEW_COLUMNS = {
    "LEAD AGENCY": "lead_agency", "IMPLEMENTING PARTNER": "partner", "DONOR": "donor",
    "PROVINCE": "province", "DISTRICT": "district", "MUNICIPALITY": "municipality", "WARD": "ward",
    "HOLDING CENTRE / DISPLACEMENT SITE": "holding_centre", "TYPE SPECIFIC LOCATION": "type_specific_location",
    "LOCATION TYPE": "location_type", "SECTOR": "sector", "AREA OF RESPONSIBILITY (AOR)": "aor",
    "DISASTER/RESPONSE PLAN": "response_plan", "ACTIVITY ": "activity",
    "ACTIVITY DESCRIPTION ": "activity_description", "RESPONSE MODALITY ": "modality",
    "ACTIVITY INDICATOR": "activity_indicator", "ACTIVITY INDICATOR UNIT": "activity_indicator_unit",
    "ACTIVITY TARGET": "activity_target", "ACTIVITY REACHED": "activity_reached",
    "RELIEF ITEMS (Standard In-Kind items)": "relief_items",
    "RELIEF ITEM DESCRIPTION": "relief_item_description", "RELIEF ITEM UNIT": "relief_item_unit",
    "NUMBER OF RELIEF ITEMS PLANNED": "relief_items_planned",
    "NUMBER OF RELIEF ITEMS DISTRIBUTED": "relief_items_distributed",
    "CASH DELIVERY MECHANISM": "cash_delivery_mechanism", "CASH CONDITIONALITY": "cash_conditionality",
    "FSP/DELIVERY AGENT": "fsp_delivery_agent", "CASH BENEFICIARY UNIT": "cash_beneficiary_unit",
    "CASH TRANSFER VALUE PER UNIT (USD)": "cash_transfer_value_per_unit",
    "CASH FREQUENCY OF TRANSFER ": "cash_frequency",
    "TOTAL AMOUNT OF EXPECTED CASH TRANSFER (USD)": "total_expected_cash_transfer",
    "TOTAL TRANSFER/DISBURSED AMOUNT (USD)": "total_disbursed_amount",
    "HOUSEHOLDS TARGETED": "hh_targeted", "PEOPLE TARGETED (Individuals)": "people_targeted",
    "HOUSEHOLDS REACHED": "hh_reached", "TOTAL NUMBER OF BENEFICIARIES REACHED (people/individuals)": "people_reached",
    "GIRLS (< 18 yrs)": "girls", "BOYS (< 18 yrs)": "boys", "WOMEN (18+ yrs)": "women", "MEN  (18+ yrs)": "men",
    "ELDERLY WOMEN (60 plus)": "elderly_women", "ELDERLY MEN (60 plus)": "elderly_men",
    "PEOPLE WITH DISABILITIES": "pwd", "ORGANISATIONS or INSTITUTIONS ": "organisations_institutions",
    "ACTIVITY STATUS ": "status", " ACTIVITY START DATE": "start_date",
    "ACTIVITY END DATE": "end_date", "NOTES": "notes", "EDIT DATE": "edit_date",
}
FIVEW_DISPLAY_HEADERS = {column: source.strip() for source, column in FIVEW_COLUMNS.items()}


def load_5w(path, sheet_name="5W_Data_Entry", header_row=6):
    wb = openpyxl.load_workbook(path, data_only=True)
    ws = wb[sheet_name]
    activity_taxonomy = load_activity_taxonomy(wb)
    headers = [ws.cell(row=header_row, column=c).value for c in range(1, ws.max_column + 1)]
    rows = []
    source_rows = []
    for r in range(header_row + 1, ws.max_row + 1):
        vals = [ws.cell(row=r, column=c).value for c in range(1, len(headers) + 1)]
        if all(v in (None, "") for v in vals):
            continue
        rows.append(dict(zip(headers, vals)))
        source_rows.append(r)
    df = pd.DataFrame(rows)
    df = df.rename(columns={k: v for k, v in FIVEW_COLUMNS.items() if k in df.columns})
    keep = list(FIVEW_COLUMNS.values())
    for col in keep:
        if col not in df.columns:
            df[col] = np.nan
    df = df[["partner", "district", "municipality", "ward"] + [c for c in keep if c not in ("partner", "district", "municipality", "ward")]]
    df["source_row"] = source_rows
    for c in ["people_reached", "hh_reached", "girls", "boys", "women", "men", "elderly_women", "elderly_men",
              "pwd", "people_targeted", "hh_targeted", "activity_target", "activity_reached",
              "relief_items_planned", "relief_items_distributed", "cash_transfer_value_per_unit",
              "total_expected_cash_transfer", "total_disbursed_amount"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["municipality"] = df["municipality"].map(normalize_palika_name)
    # Source sheet mixes real dates, typed text, and blanks in the same column - coerce to a
    # single consistent type so later display/serialization doesn't choke on the mix.
    for c in ["start_date", "end_date"]:
        # dayfirst=True: Nepal data is DD/MM/YYYY: without this, ambiguous dates like
        # 03/10/2026 silently get misread as March instead of 3 October.
        df[c] = pd.to_datetime(df[c], errors="coerce", dayfirst=True).dt.strftime("%d-%b-%Y")
        df[c] = df[c].fillna("")
    out_ind_sub = df.apply(
        lambda row: classify_row(
            row["activity"], row["activity_indicator"], row["activity_indicator_unit"], row["location_type"],
            row["holding_centre"], row["type_specific_location"], activity_taxonomy,
        ),
        axis=1,
    )
    df["output"] = out_ind_sub.apply(lambda result: result[0])
    df["indicator"] = out_ind_sub.apply(lambda result: result[1])
    df["subindicator"] = out_ind_sub.apply(lambda result: result[2])
    return df


def progress_value(row):
    """Return progress in the unit used by the mapped programme indicator."""
    indicator = row.get("indicator")
    if indicator in MANUAL_TRACKED_INDICATORS or indicator == WATER_QUALITY_INDICATOR:
        reached = pd.to_numeric(row.get("activity_reached"), errors="coerce")
        return reached if pd.notna(reached) and reached > 0 else 0
    if indicator == "Children using safe WASH facilities in learning spaces":
        children = [pd.to_numeric(row.get(col), errors="coerce") for col in ("girls", "boys")]
        if any(pd.notna(value) for value in children):
            return sum(value for value in children if pd.notna(value))
    if indicator == "Women & girls reached with MHM services":
        women_and_girls = [
            pd.to_numeric(row.get(col), errors="coerce") for col in ("girls", "women")
        ]
        if any(pd.notna(value) for value in women_and_girls):
            return sum(value for value in women_and_girls if pd.notna(value))
    if pd.notna(row["people_reached"]) and row["people_reached"] > 0:
        return row["people_reached"]
    return 0


def _reported_value(row, preferred_columns):
    for col in preferred_columns:
        value = pd.to_numeric(row.get(col), errors="coerce")
        if pd.notna(value):
            return float(value)
    return np.nan


def target_value(row):
    """Read target from the activity-indicator unit's matching target field."""
    direct_target = _reported_value(row, ["activity_target"])
    if pd.notna(direct_target) and direct_target > 0:
        return direct_target
    unit = str(row.get("activity_indicator_unit", "")).casefold()
    if "household" in unit:
        columns = ["hh_targeted"]
    elif any(term in unit for term in ("people", "person", "individual", "child", "beneficiar")):
        columns = ["people_targeted"]
    elif any(term in unit for term in ("kit", "material", "package", "relief item")):
        columns = ["relief_items_planned"]
    else:
        columns = ["people_targeted", "hh_targeted"] if unit in ("", "nan", "none") else []
    target = _reported_value(row, columns)
    return target if pd.notna(target) and target > 0 else 0


def reached_value(row):
    """Read achieved value in the same unit as the row's target."""
    direct_reached = _reported_value(row, ["activity_reached"])
    if pd.notna(direct_reached):
        return direct_reached
    unit = str(row.get("activity_indicator_unit", "")).casefold()
    if "household" in unit:
        columns = ["hh_reached"]
    elif any(term in unit for term in ("people", "person", "individual", "child", "beneficiar")):
        columns = ["people_reached"]
    elif any(term in unit for term in ("kit", "material", "package", "relief item")):
        columns = ["relief_items_distributed"]
    else:
        columns = ["people_reached", "hh_reached"] if unit in ("", "nan", "none") else []
    return _reported_value(row, columns)


def build_indicator_summary(df):
    """Sum reported row-level reach for each tracked indicator."""
    df = df.copy()
    df["progress"] = df.apply(progress_value, axis=1)
    agg = df.groupby("indicator", dropna=True)["progress"].sum().reset_index()

    summary = INDICATORS_DF.merge(agg, on="indicator", how="left")
    summary["progress"] = summary["progress"].fillna(0)
    summary.loc[(~summary["tracked_in_5w"]) & (~summary["indicator"].isin(MANUAL_TRACKED_INDICATORS)), "progress"] = np.nan
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


def build_activity_target_summary(df, output=None):
    """Return one row per reported 5W Activity Target, without summing unlike units."""
    records = df.copy()
    records["activity_target"] = records.apply(target_value, axis=1)
    records["activity_reached"] = records.apply(reached_value, axis=1)
    records = records[records["activity_target"] > 0].copy()
    if output is not None:
        records = records[records["output"] == output].copy()
    records["completion_pct"] = records["activity_reached"] / records["activity_target"] * 100
    records["activity_label"] = records["activity_indicator"].where(
        records["activity_indicator"].notna() & records["activity_indicator"].astype(str).str.strip().ne(""),
        records["activity"],
    )
    records["activity_unit"] = records["activity_indicator_unit"].where(
        records["activity_indicator_unit"].notna() & records["activity_indicator_unit"].astype(str).str.strip().ne(""),
        records["relief_item_unit"],
    )
    records["activity_unit"] = records["activity_unit"].fillna("Units")
    if records.empty:
        records["target_label"] = pd.Series(index=records.index, dtype="string")
    else:
        records["target_label"] = records.apply(
            lambda row: f"Row {int(row['source_row'])} | {row['activity_label']} | {row['municipality']}",
            axis=1,
        )
    return records


def build_palika_output_summary(df):
    """Sum reported row-level reach by Palika and Output."""
    working = df.copy()
    working["progress"] = working["people_reached"].fillna(0)
    return working.groupby(["municipality", "output"], dropna=True, as_index=False)["progress"].sum()


DEMO_COLS = ["people_reached", "hh_reached", "girls", "boys", "women", "men", "elderly_women", "elderly_men", "pwd"]


def build_beneficiary_reconciliation(df):
    """Return rows where reported people reached differs from sex/age disaggregation."""
    columns = [
        "source_row", "municipality", "ward", "activity", "activity_indicator",
        "people_reached", "girls", "boys", "women", "men",
    ]
    records = df[columns].copy()
    demographic_columns = ["girls", "boys", "women", "men"]
    disaggregated = records[demographic_columns].apply(pd.to_numeric, errors="coerce")
    records["disaggregated_total"] = disaggregated.sum(axis=1, min_count=1)
    records["difference"] = records["people_reached"] - records["disaggregated_total"]
    reported_both = records["people_reached"].notna() & records["disaggregated_total"].notna()
    return records[reported_both & records["difference"].ne(0)].copy()


def build_palika_summary(df):
    """Per-Palika totals from the beneficiary figures reported in each 5W row."""
    df = df.copy()
    df["municipality"] = df["municipality"].map(normalize_palika_name)
    rows = []
    for palika in PALIKAS:
        sub = df[df["municipality"] == palika]
        row = {"palika": palika, "activities": len(sub)}
        for c in DEMO_COLS:
            row[c] = sub[c].fillna(0).sum()
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
        "source_row": "Source 5W row",
        "lead_agency": "Lead agency", "partner": "Implementing partner", "donor": "Donor",
        "province": "Province", "district": "District", "municipality": "Palika",
        "ward": "Ward", "holding_centre": "Holding centre / displacement site",
        "type_specific_location": "Specific location", "location_type": "Location type",
        "sector": "Sector", "aor": "Area of responsibility", "response_plan": "Disaster / response plan",
        "activity": "Activity", "activity_description": "Activity description", "modality": "Modality",
        "activity_indicator": "Activity indicator", "activity_indicator_unit": "Activity indicator unit",
        "activity_target": "Activity target", "activity_reached": "Activity reached",
        "relief_items": "Relief items", "relief_item_description": "Relief item description",
        "relief_item_unit": "Relief item unit", "relief_items_planned": "Relief items planned",
        "relief_items_distributed": "Relief items distributed",
        "cash_delivery_mechanism": "Cash delivery mechanism", "cash_conditionality": "Cash conditionality",
        "fsp_delivery_agent": "FSP / delivery agent", "cash_beneficiary_unit": "Cash beneficiary unit",
        "cash_transfer_value_per_unit": "Cash transfer value per unit (USD)",
        "cash_frequency": "Cash frequency", "total_expected_cash_transfer": "Expected cash transfer (USD)",
        "total_disbursed_amount": "Disbursed amount (USD)",
        "hh_targeted": "Households targeted", "people_targeted": "People targeted",
        "hh_reached": "Households reached", "people_reached": "People reached",
        "record_progress": "Mapped indicator progress", "girls": "Girls (<18)", "boys": "Boys (<18)",
        "women": "Women (18+)", "men": "Men (18+)", "elderly_women": "Elderly women (60+)",
        "elderly_men": "Elderly men (60+)", "pwd": "People with disabilities",
        "organisations_institutions": "Organisations / institutions", "status": "Activity status",
        "start_date": "Start date", "end_date": "End date", "notes": "Notes", "edit_date": "Edit date",
        "output": "Mapped output", "indicator": "Mapped indicator",
        "subindicator": "Mapped sub-indicator",
    })

    quality_rows = []
    for source_column in FIVEW_COLUMNS.values():
        label = FIVEW_DISPLAY_HEADERS[source_column]
        values = df[source_column]
        missing = values.isna() | values.astype(str).str.strip().eq("")
        quality_rows.append({
            "Field": label, "Records missing": int(missing.sum()),
            "Records populated": int((~missing).sum()), "Completeness (%)": round((~missing).mean() * 100, 1),
        })
    mapped = df["output"].notna() & df["indicator"].notna()
    quality_rows.append({
        "Field": "Unmapped output or programme indicator",
        "Records missing": int((~mapped).sum()),
        "Records populated": int(mapped.sum()),
        "Completeness (%)": round(mapped.mean() * 100, 1),
    })
    quality = pd.DataFrame(quality_rows)
    unmapped = df[~mapped][[
        "partner", "municipality", "ward", "activity", "activity_indicator",
        "activity_indicator_unit", "activity_description", "status", "output", "indicator",
    ]].rename(columns={
        "partner": "Implementing partner", "municipality": "Palika", "ward": "Ward",
        "activity": "Activity", "activity_description": "Activity description", "status": "Activity status",
        "activity_indicator": "5W activity indicator",
        "activity_indicator_unit": "5W activity indicator unit", "output": "Mapped output",
        "indicator": "Mapped programme indicator",
    })

    sheets = {
        "Indicator Tracker": indicator_tracker,
        "Palika Tracker": palika_tracker,
        "5W Activity Register": register,
        "Data Quality": quality,
        "Beneficiary Reconciliation": build_beneficiary_reconciliation(df).rename(columns={
            "source_row": "Source 5W row", "municipality": "Palika", "ward": "Ward",
            "activity": "Activity", "activity_indicator": "Activity indicator",
            "people_reached": "People reached", "girls": "Girls (<18)", "boys": "Boys (<18)",
            "women": "Women (18+)", "men": "Men (18+)",
            "disaggregated_total": "Disaggregated total", "difference": "Difference",
        }),
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
