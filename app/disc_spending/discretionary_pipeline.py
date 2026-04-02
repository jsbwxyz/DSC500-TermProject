"""
Discretionary Spending Intelligence Pipeline
=============================================
Combines two data layers:
  1. BLS CPI   - which discretionary categories are holding price & demand
  2. Google Trends - which specific products within those categories are trending

How it works:
  - Pulls raw CPI index values from the BLS API
  - Computes MoM and YoY % changes manually (no API key needed)
  - Prints a monthly detail table for the past 12 months per category
  - Prints a summary table ranked by YoY pressure
  - For the top N categories, drills into Google Trends for product-level signals

Requirements:
    pip install requests pytrends pandas tabulate

Usage:
    python discretionary_pipeline.py

Output:
    - Console: monthly detail + summary + trends tables
    - discretionary_bls_monthly.csv
    - discretionary_bls_summary.csv
    - discretionary_trends_summary.csv
"""

import time
import requests
import pandas as pd
from pytrends.request import TrendReq
from tabulate import tabulate

# ── CONFIG ─────────────────────────────────────────────────────────────────────

BLS_API_KEY      = ""          # Free key at https://www.bls.gov/developers/
                                # No key: 25 req/day. With key: 500 req/day.
EXPORT_CSV       = True        # Write results to CSV?
BLS_START_YEAR   = 2025        # Need enough history for YoY — don't go below 2023
BLS_END_YEAR     = 2026
TOP_N            = 5           # Top N BLS categories to drill into with Trends
TRENDS_TIMEFRAME = "today 12-m"

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

# Product-level Google Trends keywords per category (max 5 per batch)
TRENDS_KEYWORDS = {
    "Recreation":             ["fitness tracker", "kayak", "camping gear", "yoga mat", "hiking boots"],
    "Food Away From Home":    ["fast casual dining", "meal kit delivery", "food delivery", "brunch", "omakase"],
    "Apparel":                ["sneakers", "athleisure", "luxury handbag", "vintage clothing", "workwear"],
    "Personal Care":          ["skincare", "hair care", "perfume", "electric toothbrush", "massage gun"],
    "Education":              ["online course", "coding bootcamp", "tutoring", "language learning app", "MBA"],
    "Sporting Goods":         ["pickleball paddle", "golf clubs", "running shoes", "home gym", "bicycle"],
    "Audio / Video":          ["OLED TV", "soundbar", "noise cancelling headphones", "projector", "streaming device"],
    "Pets and Pet Products":  ["dog food", "cat tree", "pet insurance", "dog bed", "pet grooming"],
    "Alcohol Away From Home": ["craft cocktail", "wine bar", "sake", "whiskey tasting", "rooftop bar"],
    "New Vehicles":           ["electric vehicle", "hybrid car", "truck lease", "car deal", "EV incentive"],
}


# ── BLS LAYER ──────────────────────────────────────────────────────────────────

def to_float(v):
    """Return float or None — handles BLS dash placeholders."""
    try:
        return float(v)
    except (ValueError, TypeError):
        return None


def fetch_bls_cpi(series_dict: dict, start_year: int, end_year: int) -> pd.DataFrame:
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
    if BLS_API_KEY:
        payload["registrationkey"] = BLS_API_KEY
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


# ── GOOGLE TRENDS LAYER ────────────────────────────────────────────────────────

def fetch_trends_for_categories(
    categories: list,
    keywords_map: dict,
    timeframe: str = "today 12-m",
) -> pd.DataFrame:
    """
    For each category fetch Google Trends interest for its keywords.
    Scores are 0-100 relative scale (100 = peak search interest).
    Batched in groups of 5 to stay within pytrends limits.
    """
    pytrends = TrendReq(hl="en-US", tz=300)
    all_rows  = []

    for cat in categories:
        keywords = keywords_map.get(cat, [])
        if not keywords:
            continue

        print(f"[Trends] {cat}: {keywords}")
        batches        = [keywords[i:i+5] for i in range(0, len(keywords), 5)]
        keyword_scores = {}

        for batch in batches:
            try:
                pytrends.build_payload(batch, timeframe=timeframe, geo="US")
                df_interest = pytrends.interest_over_time()
                if df_interest.empty:
                    continue
                for kw in batch:
                    if kw in df_interest.columns:
                        keyword_scores[kw] = round(df_interest[kw].mean(), 1)
            except Exception as e:
                print(f"  [warn] Trends error for batch {batch}: {e}")
            time.sleep(1.5)

        if not keyword_scores:
            continue

        sorted_kws = sorted(keyword_scores.items(), key=lambda x: x[1], reverse=True)
        for rank, (kw, score) in enumerate(sorted_kws, start=1):
            all_rows.append({
                "Category":     cat,
                "Keyword":      kw,
                "Avg Interest": score,
                "Rank in Cat":  rank,
            })

    return pd.DataFrame(all_rows)


# ── MAIN ───────────────────────────────────────────────────────────────────────

def main():
    # --- BLS ---
    raw_bls = fetch_bls_cpi(BLS_SERIES, BLS_START_YEAR, BLS_END_YEAR)

    # Monthly detail — last 12 months
    monthly = monthly_detail(raw_bls, months=12)
    print("\n=== BLS Monthly Detail (last 12 months, all categories) ===")
    for cat, grp in monthly.groupby("Category"):
        print(f"\n  {cat}")
        print(tabulate(
            grp.drop(columns="Category"),
            headers="keys",
            tablefmt="simple",
            showindex=False,
            floatfmt=".2f",
        ))

    if EXPORT_CSV:
        monthly.to_csv("app/disc_spending/data/discretionary_bls_monthly.csv", index=False)
        print("\nSaved: discretionary_bls_monthly.csv")

    # Summary
    bls_summary = summarize_bls(raw_bls)
    print("\n=== BLS Discretionary CPI Summary (latest month) ===")
    print(tabulate(bls_summary, headers="keys", tablefmt="simple", showindex=False, floatfmt=".2f"))

    if EXPORT_CSV:
        bls_summary.to_csv("app/disc_spending/data/discretionary_bls_summary.csv", index=False)
        print("Saved: discretionary_bls_summary.csv")

    # --- Google Trends (top N by YoY) ---
    top_categories = (
        bls_summary[bls_summary["YoY %"].notna()]
        .head(TOP_N)["Category"]
        .tolist()
    )
    print(f"\nDrilling into top {TOP_N} categories via Google Trends: {top_categories}")

    trends_df = fetch_trends_for_categories(top_categories, TRENDS_KEYWORDS, TRENDS_TIMEFRAME)

    if not trends_df.empty:
        print("\n=== Google Trends - Top Products by Category (top 3 per category) ===")
        top3 = (
            trends_df[trends_df["Rank in Cat"] <= 3]
            .sort_values(["Category", "Rank in Cat"])
            .reset_index(drop=True)
        )
        print(tabulate(top3, headers="keys", tablefmt="simple", showindex=False, floatfmt=".1f"))

        if EXPORT_CSV:
            trends_df.to_csv("app/disc_spending/data/discretionary_trends_summary.csv", index=False)
            print("Saved: discretionary_trends_summary.csv")
    else:
        print("[Trends] No data returned.")


if __name__ == "__main__":
    main()