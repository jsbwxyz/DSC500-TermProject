"""
Discretionary Spending Intelligence Pipeline
Main orchestration script for fetching and processing spending data
"""

import sys
from pathlib import Path

# Add project root to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tabulate import tabulate
from app.shared_utils import get_data_dir
from tools.fetch_bls import BLS_SERIES, fetch_bls_cpi, monthly_detail, summarize_bls
from tools.fetch_trends import FALLBACK_KEYWORDS, fetch_trends_for_categories
from tools.db_uploader import SpendingDatabaseUploader


# ── CONFIG ─────────────────────────────────────────────────────────────────────

BLS_API_KEY      = ""          # Free key at https://www.bls.gov/developers/
                                # No key: 25 req/day. With key: 500 req/day.
EXPORT_CSV       = True        # Write results to CSV?
UPLOAD_TO_DB     = True        # Upload results to database?
BLS_START_YEAR   = 2025        # Need enough history for YoY — don't go below 2023
BLS_END_YEAR     = 2026
TOP_N            = 5           # Top N BLS categories to drill into with Trends
TRENDS_TIMEFRAME = "today 12-m"
USE_DB_KEYWORDS  = True        # Use keywords from database instead of hardcoded
DB_KEYWORDS_MONTHS = 3         # How many months back to query keywords from DB


def main():
    # Get data directory
    data_dir = get_data_dir('spending')

    # --- BLS ---
    raw_bls = fetch_bls_cpi(BLS_SERIES, BLS_START_YEAR, BLS_END_YEAR, BLS_API_KEY)

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
        csv_path = data_dir / "discretionary_bls_monthly.csv"
        monthly.to_csv(csv_path, index=False)
        print(f"\nSaved: {csv_path}")

    # Summary
    bls_summary = summarize_bls(raw_bls)
    print("\n=== BLS Discretionary CPI Summary (latest month) ===")
    print(tabulate(bls_summary, headers="keys", tablefmt="simple", showindex=False, floatfmt=".2f"))

    if EXPORT_CSV:
        csv_path = data_dir / "discretionary_bls_summary.csv"
        bls_summary.to_csv(csv_path, index=False)
        print(f"Saved: {csv_path}")

    # --- Google Trends (top N by YoY) ---
    top_categories = (
        bls_summary[bls_summary["YoY %"].notna()]
        .head(TOP_N)["Category"]
        .tolist()
    )
    print(f"\nDrilling into top {TOP_N} categories via Google Trends: {top_categories}")

    trends_df = fetch_trends_for_categories(
        top_categories,
        FALLBACK_KEYWORDS,
        TRENDS_TIMEFRAME,
        use_db_keywords=USE_DB_KEYWORDS,
        months_back=DB_KEYWORDS_MONTHS
    )

    if not trends_df.empty:
        print("\n=== Google Trends - Top Products by Category (top 3 per category) ===")
        top3 = (
            trends_df[trends_df["Rank in Cat"] <= 3]
            .sort_values(["Category", "Rank in Cat"])
            .reset_index(drop=True)
        )
        print(tabulate(top3, headers="keys", tablefmt="simple", showindex=False, floatfmt=".1f"))

        if EXPORT_CSV:
            csv_path = data_dir / "discretionary_trends_summary.csv"
            trends_df.to_csv(csv_path, index=False)
            print(f"Saved: {csv_path}")
    else:
        print("[Trends] No data returned.")

    # --- Upload to Database ---
    if UPLOAD_TO_DB:
        print("\n" + "=" * 70)
        print("Uploading to database...")
        print("=" * 70)

        uploader = SpendingDatabaseUploader()
        if uploader.connect():
            uploader.create_tables()

            # Upload BLS data
            bls_count = uploader.upload_bls_data(raw_bls)
            print(f"Uploaded {bls_count} BLS CPI records")

            # Upload Trends data
            if not trends_df.empty:
                trends_count = uploader.upload_trends_data(trends_df)
                print(f"Uploaded {trends_count} Google Trends records")

            uploader.close()


if __name__ == "__main__":
    main()
