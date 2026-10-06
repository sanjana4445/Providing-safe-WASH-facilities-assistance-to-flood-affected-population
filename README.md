# Rasuwa WASH Response Dashboard

A Streamlit dashboard that reads UNICEF's 5W tool export and tracks progress against
the Programme Document's 5 Outputs / 10 indicators, activity records, and georeferenced
project sites for Chay-Ya Nepal and UNICEF.

## Dashboard views

- **Sidebar:** upload a refreshed 5W workbook, see the project countdown (15 September–31 December 2026), and check the last dashboard update time.
- **Overview:** five programme outputs, the ten PD indicator targets, and an output-selected activity-target chart. Each bar compares one 5W Activity Target with its Activity Reached value; targets are not pooled across activities or units.
- **Palika detail:** a four-Palika comparison chart, selected activity fields, and an expandable complete 5W register.
- **Activities by output:** activity-type breakdowns with completed/ongoing status colors.
- **Planning:** one board for all ten programme indicator targets, with progress, remaining target, and a completion-ranked priority chart. Targets with different units are compared by completion percentage.
- **Beneficiary demographics:** sex and age disaggregation, with elderly and disability counts shown separately.
- **Beneficiary explorer:** select an output, WASH activity, and people/household reach measure.
- **Project map:** embedded Google My Maps plus filtered 5W records. Pins are not automatically linked to activities because the source has no GPS coordinates or shared site ID.

## What's in this folder

| File | Purpose |
|---|---|
| `app.py` | The dashboard itself (Streamlit UI) |
| `data_processing.py` | Reads meaningful 5W fields, maps activity rows to an Output/Indicator, and computes progress |
| `Rasuwa_-_UNICEF_WASH_NEPAL_5Ws_Data_Entry.xlsx` | The data the dashboard reads by default |
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
- **Palika Tracker:** reach and demographic disaggregation by municipality.
- **5W Activity Register:** all 50 meaningful source fields plus mapped output/indicator and progress.
- **Data Quality:** completeness for each mapped source field.
- **Unmapped Activities:** rows that need mapping review.

The export is generated from the workbook currently loaded in the dashboard, including an uploaded refresh. It does not modify the source UNICEF workbook.

In the bundled 5W export, only three mapped activity rows have both an activity target and a reached value, all under Output 4. Other outputs display a no-target message until those fields are reported. An unmapped target row is flagged separately and is not included in an output chart.

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

---

## How progress is calculated (read this before trusting the numbers)

- Every 5W row is matched to one of the 5 Outputs by its **Activity**. If the location is a
  school, CFS, or health facility, that overrides the activity-based guess, since Output 4
  is defined by *where* the work happens, not what kind of work it is.
- **Water, sanitation, and school/CFS activities**: progress is a straight sum of "Total
  beneficiaries reached" across matching rows.
- **Critical WASH supplies and hygiene promotion**: multiple item rows (hygiene kit, bucket,
  chlorination tablets, different IEC materials) often report the *same* households once per
  item. Summing those would count the same people several times over. The dashboard instead
  takes the single largest reported round per Palika for each of these two indicators.
- Rows using an Activity this dashboard can't yet map to an Output (check the sidebar for a
  warning) are excluded from totals rather than guessed at \u2014 open the raw sheet to see them.
- Output 1 (coordination meetings, assessment visits) isn't in the 5W tool at all \u2014 track
  those two indicators separately, the same way you have been.

The 5 Outputs, 10 indicators, and their targets are fixed in `data_processing.py`
(`INDICATORS` list), taken from the Chay-Ya Monitoring Matrix. If a target ever changes,
that's the only place you need to edit \u2014 everything else recalculates automatically.
