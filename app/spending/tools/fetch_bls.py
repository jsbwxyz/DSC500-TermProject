"""
BLS CPI Data Fetcher
Fetches and processes Consumer Price Index data from the Bureau of Labor Statistics API
"""

import requests
import pandas as pd


# Discretionary CPI series — label: BLS series ID
# Series IDs verified against https://www.bls.gov/cpi/tables/supplemental-files/home.htm
BLS_SERIES = {
    "Recreation":             "CUSR0000SAR",
    "Food Away From Home":    "CUSR0000SEFV",
    "Apparel":                "CUSR0000SAA",
    "Personal Care":          "CUSR0000SAG1",
    "Education":              "CUSR0000SAE1",
    "Sporting Goods":         "CUSR0000SSEA",      # sporting goods & hobby
    "Audio / Video":          "CUSR0000SEEE",      # video & audio equipment
    "Pets and Pet Products":  "CUSR0000SERE",      # pets, products & services
    "Alcohol Away From Home": "CUSR0000SACL2",
    "New Vehicles":           "CUSR0000SETA01",
}


def to_float(v):
    """Return float or None — handles BLS dash placeholders."""
    try:
        return float(v)
    except (ValueError, TypeError):
        return None


def fetch_bls_cpi(series_dict: dict, start_year: int, end_year: int, api_key: str = "") -> pd.DataFrame:
    """
    Pull raw CPI index values from BLS API v2.
    MoM and YoY are computed manually afterward — the BLS only returns
    pre-computed pct_changes when a registered API key is provided.
    """
    url = "https://api.bls.gov/publicAPI/v2/timeseries/data/"

    payload = {
        "seriesid":      list(series_dict.values()),
        "startyear":     str(start_year),
        "endyear":       str(end_year),
        "annualaverage": False,
    }
    if api_key:
        payload["registrationkey"] = api_key
        payload["calculations"]    = True   # only works with a key

    print(f"\n[BLS] Fetching {len(series_dict)} series ({start_year}-{end_year})...")
    resp = requests.post(url, json=payload, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    if data["status"] != "REQUEST_SUCCEEDED":
        raise RuntimeError(f"BLS API error: {data.get('message', data)}")

    returned_ids = [s["seriesID"] for s in data["Results"]["series"]]
    requested_ids = list(series_dict.values())
    missing = set(requested_ids) - set(returned_ids)
    if missing:
        bad_labels = [k for k, v in series_dict.items() if v in missing]
        print(f"  [warn] No data returned for: {bad_labels} — check series IDs")

    id_to_label = {v: k for k, v in series_dict.items()}
    rows = []

    for series in data["Results"]["series"]:
        label = id_to_label.get(series["seriesID"], series["seriesID"])
        for obs in series["data"]:
            if obs["period"] == "M13":
                continue
            rows.append({
                "category":  label,
                "series_id": series["seriesID"],
                "year":      int(obs["year"]),
                "month":     int(obs["period"][1:]),
                "value":     to_float(obs["value"]),
            })

    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(
        df["year"].astype(str) + "-" + df["month"].astype(str).str.zfill(2) + "-01"
    )
    df = df.sort_values(["category", "date"]).reset_index(drop=True)

    # Compute MoM and YoY manually from raw index values
    df["pct_1m"]  = df.groupby("category")["value"].pct_change(periods=1)  * 100
    df["pct_12m"] = df.groupby("category")["value"].pct_change(periods=12) * 100

    return df


def monthly_detail(df: pd.DataFrame, months: int = 12) -> pd.DataFrame:
    """
    Return a tidy table of the last N months for every category,
    with CPI value, MoM %, and YoY %.
    """
    latest_date = df["date"].max()
    cutoff      = latest_date - pd.DateOffset(months=months - 1)
    recent      = df[df["date"] >= cutoff].copy()

    recent["Date"]      = recent["date"].dt.strftime("%Y-%m")
    recent["CPI Value"] = recent["value"].round(3)
    recent["MoM %"]     = recent["pct_1m"].round(2)
    recent["YoY %"]     = recent["pct_12m"].round(2)

    return (
        recent[["category", "Date", "CPI Value", "MoM %", "YoY %"]]
        .rename(columns={"category": "Category"})
        .sort_values(["Category", "Date"])
        .reset_index(drop=True)
    )


def summarize_bls(df: pd.DataFrame) -> pd.DataFrame:
    """
    One summary row per category using the most recent month.
    Demand signal based on YoY: Strong >= 3%, Moderate 1-3%, Soft < 1%.
    """
    latest_date = df["date"].max()
    cutoff_6m   = latest_date - pd.DateOffset(months=6)
    rows = []

    for cat, grp in df.groupby("category"):
        grp    = grp.sort_values("date")
        recent = grp[grp["date"] == latest_date]
        if recent.empty:
            recent = grp.iloc[[-1]]
        recent = recent.iloc[0]

        avg_mom_6m = grp[grp["date"] > cutoff_6m]["pct_1m"].dropna().mean()
        yoy        = recent["pct_12m"]

        if pd.isna(yoy):
            signal = "N/A"
        elif yoy >= 3.0:
            signal = "Strong"
        elif yoy >= 1.0:
            signal = "Moderate"
        else:
            signal = "Soft"

        rows.append({
            "Category":      cat,
            "As Of":         recent["date"].strftime("%Y-%m"),
            "CPI Value":     round(recent["value"], 3)  if pd.notna(recent["value"])  else None,
            "MoM %":         round(recent["pct_1m"], 2) if pd.notna(recent["pct_1m"]) else None,
            "YoY %":         round(yoy, 2)              if pd.notna(yoy)              else None,
            "Avg MoM 6m %":  round(avg_mom_6m, 2)       if pd.notna(avg_mom_6m)       else None,
            "Demand Signal": signal,
        })

    summary = pd.DataFrame(rows)
    summary = summary.sort_values("YoY %", ascending=False, na_position="last")
    return summary.reset_index(drop=True)
