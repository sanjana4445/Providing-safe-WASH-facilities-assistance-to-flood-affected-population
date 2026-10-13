# Providing safe WASH facilities & assistance to flood-affected population

The Rasuwa WASH response dashboard reads UNICEF's 5W tool export and tracks progress against
the Programme Document's 5 Outputs / 10 indicators, activity records, and georeferenced
project sites for Chay-Ya Nepal and UNICEF.

## Dashboard views

- **Sidebar:** upload a refreshed 5W workbook, see the project countdown (15 September–31 December 2026), and check the last dashboard update time.
- **Overview:** five programme outputs, output-level row-reported reach, all ten PD indicator targets with the mapped 5W activity details, beneficiary totals, and an output-selected activity-target chart.
- **Palika detail:** a four-Palika comparison chart, output/activity progress rollup, selected activity fields, and an expandable complete 5W register.
- **Activities by output:** activity-type breakdowns with completed/ongoing status colors, plus an output/activity/sub-activity rollup of unit-aware target/reached totals and row-reported people, household, age/sex, elderly, and disability figures.
- **Planning:** one board for all ten programme indicator targets, with progress, remaining target, and a completion-ranked priority chart. Targets with different units are compared by completion percentage.
- **Beneficiary demographics:** filter by programme output, activity, and sub-activity; review reported sex and age disaggregation, with elderly and disability counts shown separately.
- **Beneficiary explorer:** filter hierarchically by programme output, target indicator, workbook activity, and sub-activity; compare people or household reach across Palikas.
- **Manual activity entry:** record only the three programme targets not captured in the 5W Excel sheet: coordination meetings, needs-and-damage assessment missions, and community feedback mechanisms. All other activity and beneficiary data comes from the workbook.
- **Project map:** embedded Google My Maps plus output/activity-filtered progress and 5W records. Pins are not automatically linked to activities because the source has no GPS coordinates or shared site ID.

## What's in this folder

| File | Purpose |
|---|---|
| `app.py` | The dashboard itself (Streamlit UI) |
| `data_processing.py` | Reads meaningful 5W fields, maps activity rows to an Output/Indicator, and computes progress |
| `Rasuwa - UNICEF_WASH_NEPAL_5Ws_Data_Entry.xlsx` | The data the dashboard reads by default |
| `requirements.txt` | Python packages needed |
| `.streamlit/config.toml` | Colour theme |

---

## 1. Run it on your own computer first (optional but recommended)

```bash
pip install -r requirements.txt
streamlit run app.py
```

This opens the dashboard in your browser at `http://localhost:8501`. Check it looks right
before putting it online.

## Updating the 5W data

- **For a temporary update:** open the dashboard and upload the new `.xlsx` file in the
  sidebar's **5W Excel workbook** control. This only updates the current dashboard session.
- **For a permanent update for everyone:** replace the workbook in the GitHub repository
  and commit the change. Keep the filename
  `Rasuwa - UNICEF_WASH_NEPAL_5Ws_Data_Entry.xlsx`; if you use a different name, make
  sure it is the only `.xlsx` workbook in the repository root. Streamlit Community Cloud
  will redeploy from the updated repository. If the default workbook is missing, you can
  also upload a workbook in the sidebar for the current session.

---

## 2. Put it on GitHub

1. Go to [github.com](https://github.com) and sign in (create a free account if you don't have one).
2. Click the **+** in the top-right \u2192 **New repository**.
3. Name it something like `rasuwa-wash-dashboard`. Keep it **Public** (Streamlit Community
   Cloud's free tier needs this). Click **Create repository**.
4. On the empty repo page, click **uploading an existing file**.
5. Drag in every file from this folder \u2014 `app.py`, `data_processing.py`,
   `requirements.txt`, the `.xlsx` file, and the `.streamlit` folder (make sure
   `.streamlit/config.toml` goes in as its own subfolder, not flattened into the root).
6. Scroll down, click **Commit changes**.

## 3. Deploy on Streamlit Community Cloud

1. Go to [share.streamlit.io](https://share.streamlit.io) and sign in **with your GitHub
   account** (this is what lets it see your repo).
2. Click **Create app** \u2192 **From an existing repo**.
3. Pick the `rasuwa-wash-dashboard` repo, branch `main`, and set the main file path to
   `app.py`.
4. Click **Deploy**. The first build takes 2\u20133 minutes.
5. You'll get a permanent link like `https://rasuwa-wash-dashboard.streamlit.app` \u2014 this
   is what you share with Niroj, UNICEF, and your team.

---

## 4. Download the monitoring workbook

Use **Download Excel monitoring pack** in the dashboard sidebar to export the currently loaded 5W records. The generated workbook includes:

- **Indicator Tracker:** targets, progress, remaining reach, tracking status, and progress bars.
- **Output Summary:** average indicator completion plus separate row totals for people, households, and activity target/reached fields.
- **Activity Rollup:** output/activity/sub-activity groups with unit-aware target/reached and separate people, household, age/sex, elderly, and disability totals.
- **Palika Tracker:** reach and demographic disaggregation by municipality.
- **5W Activity Register:** all 50 meaningful source fields plus mapped output, programme indicator, sub-indicator, and progress.
- **Data Quality:** completeness for each mapped source field.
- **Unmapped Activities:** rows that need mapping review.

The export is generated from the workbook currently loaded in the dashboard, including an uploaded refresh. It does not modify the source UNICEF workbook.
Only the three targets absent from the 5W sheet (coordination meetings, assessment missions, and feedback mechanisms) are entered manually. Those records are stored separately in `manual_entries.csv`; uploading or replacing the workbook does not overwrite them. Manage these records only through the dashboard's **Manual activity entry** page. All other target and beneficiary data is read from the currently loaded workbook.

The activity-target chart uses the target/reached source fields that match each row's selected Activity Indicator unit. It keeps each 5W row separate and does not combine unlike units; a blank reached value stays unreported rather than being shown as zero. Programme indicator assignment follows the workbook's activity/output taxonomy, while indicator progress uses the relevant beneficiary field (or age/sex group for school/TLC/HCF and MHM indicators). Facility/system counts stay in activity progress rather than being added to people totals.

Every reporting tab uses the currently loaded workbook rows and mapped Output, Activity, Sub-activity, and target indicator. Rollups keep different Activity Indicator units separate and show people, household, age/sex, elderly, and disability totals in their own columns. Beneficiary totals are row sums and may overlap across activity types; they are not deduplicated because the workbook contains no beneficiary-level IDs. The overview output summary reports average indicator completion alongside beneficiary row totals; it does not combine unlike target units into one project percentage. Workbook template rows without activity or other reported values are excluded from activity counts.

The dashboard also flags rows where **Total beneficiaries reached** differs from the sum of girls, boys, women, and men, and includes those rows in a **Beneficiary Reconciliation** monitoring-export sheet. It does not silently replace either source value. Elderly and disability figures are excluded from the reconciliation because they overlap the age/sex groups.

## 5. Project site map

The **Project site map** view embeds the shared Google My Maps layer and provides a filtered 5W activity register. The current 5W export contains Palika and site-name fields but no GPS coordinates, so map pins are not automatically linked to individual activity rows. To enable that link, add coordinates or a stable site identifier to the 5W data. The My Maps layer must be shared with dashboard viewers; consider site-location sensitivity before making it public.

Dashboard records are limited to UNICEF and Chay-Ya Nepal. Other implementing-partner rows in an uploaded export are excluded.

## 6. How to update the data

You have two options, and they're not mutually exclusive:

**Quick look, for just you, this session only:**
Open the deployed app \u2192 sidebar \u2192 **"Upload the latest 5W export to refresh"** \u2192
upload your newest download from the live Google Sheet. This updates what *you* see
immediately but doesn't change what anyone else sees, and resets if you reload the page.

**Permanent update, for everyone who opens the link:**
1. Export the live UNICEF 5W Google Sheet as `.xlsx` (File \u2192 Download \u2192 Microsoft Excel).
2. On GitHub, open your repo \u2192 click the old `.xlsx` file \u2192 the pencil/upload icon \u2192
   upload the new one with the **exact same file name** \u2192 **Commit changes**.
3. Streamlit Cloud detects the change and redeploys automatically within about a minute.
   No need to touch share.streamlit.io again.

Either way, nothing about `app.py` needs to change \u2014 only the data file.

The manual-entry CSV is intentionally excluded from Git and is not part of the 5W Excel
file. It survives workbook replacements while the dashboard's local storage remains
available. Streamlit Cloud can reset local files on a redeploy, so preserving these manual
records across redeploys requires persistent external storage.

---

## How progress is calculated (read this before trusting the numbers)

- The selected **Activity** dropdown is categorized using the WASH activity taxonomy in
  the currently loaded workbook's `Activity_Indicator` sheet; it determines the programme
  output and sub-indicator. The selected **Activity Indicator** dropdown maps that activity
  to one of the ten programme indicators. A school, CFS, or health-facility location maps
  relevant water/sanitation access activities to Output 4's learning-space indicator.
  MHM/dignity activities map to the programme's MHM indicator under Output 3.
- **People and household totals** shown as beneficiary totals remain sums of the corresponding
  values reported in included 5W rows. They may overlap across activities and are not unique
  beneficiary counts; no beneficiary IDs are present in the workbook.
- The ten-indicator tracker shows a **Calculation basis / 5W source rows** column so each
  progress value can be audited against its source:
  - Safe water includes water-system repairs, community water-storage tanks, and household
    buckets/jerrycans. Matching bucket/jerrycan rows for the same location and reported
    beneficiary/sex-age cohort count once. Water filters/purifiers count under WASH supplies.
  - Sanitation includes sanitation-facility repair and emergency temporary-toilet rows,
    including school/CFS rows even when the taxonomy maps them to another output.
  - MHM is an explicit assumption: 20% of people reached by all Standard hygiene kit rows,
    rounded to a whole person. This includes every matching row in the loaded workbook.
  - The school/TLC/HCF indicator sums people reached on rows whose Location Type is School
    or Holding Centre / Displacement Site.
  - Hygiene promotion includes Standard hygiene kit and Other essential hygiene items rows;
    critical WASH supplies includes Household water treatment - Filter / purifier rows.
  - Water-quality progress sums Activity Reached on water-quality monitoring rows only;
    water-system repair counts are not treated as monitoring events. Coordination meetings,
    assessment missions, and feedback mechanisms use the separate manual-entry form.
- Beneficiary progress values can still overlap across different activities. The filtered
  indicator calculations are not deduplicated into a project-wide unique-person total.
- Rows using an Activity or Activity Indicator this dashboard can't map to a programme
  output/indicator (check the sidebar and monitoring pack for a warning) are excluded from
  indicator totals rather than guessed at \u2014 open the raw sheet to review them.
- Output 1 (coordination meetings, assessment visits) isn't in the 5W tool at all \u2014 track
  those two indicators separately, the same way you have been.

The 5 Outputs, 10 indicators, and their targets are fixed in `data_processing.py`
(`INDICATORS` list), taken from the Chay-Ya Monitoring Matrix. If a target ever changes,
that's the only place you need to edit \u2014 everything else recalculates automatically.
