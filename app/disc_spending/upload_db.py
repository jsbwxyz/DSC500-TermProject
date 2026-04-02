"""
Discretionary Spending Database Uploader
Uploads BLS CPI data and Google Trends data to database
"""

import sys
from pathlib import Path

# Add project root to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import mysql.connector
import pandas as pd
import os
from app.shared_utils import connect_database, get_data_dir

def check_bls_sync(conn, file_type='summary'):
    """Check if BLS database is synced with local CSV file"""
    print("=" * 70)
    print(f"Checking BLS CPI {file_type} sync status...")
    print("=" * 70)

    data_dir = get_data_dir('disc_spending')
    if file_type == 'summary':
        file_path = data_dir / 'discretionary_bls_summary.csv'
        date_col = 'As Of'
    else:  # monthly
        file_path = data_dir / 'discretionary_bls_monthly.csv'
        date_col = 'Date'

    file_path = str(file_path)

    if not os.path.exists(file_path):
        print(f"\nNo data file found at {file_path}")
        return {'is_synced': True, 'missing_count': 0}

    try:
        df = pd.read_csv(file_path)
    except Exception as e:
        print(f"Error reading CSV file: {e}")
        return {'is_synced': False, 'missing_count': 0}

    print(f"\nFound {len(df)} BLS records in CSV file")

    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM BLS_CPI")
    db_count = cursor.fetchone()[0]
    print(f"Found {db_count} BLS records in database")

    missing_count = 0
    for _, row in df.iterrows():
        category = row.get('Category')
        date = row.get(date_col)

        if pd.isna(category) or pd.isna(date):
            continue

        cursor.execute(
            "SELECT COUNT(*) FROM BLS_CPI WHERE CATEGORY = %s AND DATE = %s",
            (category, date)
        )
        if cursor.fetchone()[0] == 0:
            missing_count += 1

    cursor.close()

    print("\n" + "=" * 70)
    if missing_count == 0:
        print(f"✓ BLS {file_type} database is UP TO DATE")
    else:
        print(f"⚠ {missing_count} BLS {file_type} record(s) need to be uploaded")
    print("=" * 70)

    return {'is_synced': missing_count == 0, 'missing_count': missing_count}

def check_trends_sync(conn):
    """Check if Trends database is synced with local CSV file"""
    print("=" * 70)
    print("Checking Google Trends sync status...")
    print("=" * 70)

    data_dir = get_data_dir('disc_spending')
    file_path = str(data_dir / 'discretionary_trends_summary.csv')

    if not os.path.exists(file_path):
        print(f"\nNo data file found at {file_path}")
        return {'is_synced': True, 'missing_count': 0}

    try:
        df = pd.read_csv(file_path)
    except Exception as e:
        print(f"Error reading CSV file: {e}")
        return {'is_synced': False, 'missing_count': 0}

    print(f"\nFound {len(df)} Trends records in CSV file")

    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM TRENDS_DATA")
    db_count = cursor.fetchone()[0]
    print(f"Found {db_count} Trends records in database")

    missing_count = 0
    for _, row in df.iterrows():
        category = row.get('Category')
        keyword = row.get('Keyword')

        if pd.isna(category) or pd.isna(keyword):
            continue

        cursor.execute(
            "SELECT COUNT(*) FROM TRENDS_DATA WHERE CATEGORY = %s AND KEYWORD = %s",
            (category, keyword)
        )
        if cursor.fetchone()[0] == 0:
            missing_count += 1

    cursor.close()

    print("\n" + "=" * 70)
    if missing_count == 0:
        print("✓ Trends database is UP TO DATE")
    else:
        print(f"⚠ {missing_count} Trends record(s) need to be uploaded/updated")
    print("=" * 70)

    return {'is_synced': missing_count == 0, 'missing_count': missing_count}

def upload_bls_data(conn, file_type='summary'):
    """Upload BLS CPI data from CSV to database"""
    data_dir = get_data_dir('disc_spending')
    if file_type == 'summary':
        file_path = str(data_dir / 'discretionary_bls_summary.csv')
        date_col = 'As Of'
    else:  # monthly
        file_path = str(data_dir / 'discretionary_bls_monthly.csv')
        date_col = 'Date'

    df = pd.read_csv(file_path)
    print(f"\nLoaded {len(df)} BLS records from {file_path}")

    cursor = conn.cursor()
    inserted_count = 0
    skipped_count = 0

    print(f"\nUploading BLS CPI {file_type} data...")
    for _, row in df.iterrows():
        category = row.get('Category')
        date = row.get(date_col)
        cpi_value = row.get('CPI Value')
        mom_pct = row.get('MoM %')
        yoy_pct = row.get('YoY %')
        demand_signal = row.get('Demand Signal', '')

        if pd.isna(category) or pd.isna(date):
            skipped_count += 1
            continue

        # Convert NaN to None for SQL NULL
        cpi_value = None if pd.isna(cpi_value) else cpi_value
        mom_pct = None if pd.isna(mom_pct) else mom_pct
        yoy_pct = None if pd.isna(yoy_pct) else yoy_pct
        demand_signal = None if pd.isna(demand_signal) or demand_signal == '' else demand_signal

        cursor.execute(
            "SELECT COUNT(*) FROM BLS_CPI WHERE CATEGORY = %s AND DATE = %s",
            (category, date)
        )
        if cursor.fetchone()[0] == 0:
            cursor.execute("""
                INSERT INTO BLS_CPI (CATEGORY, DATE, CPI_VALUE, MOM_PCT, YOY_PCT, DEMAND_SIGNAL)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (category, date, cpi_value, mom_pct, yoy_pct, demand_signal))
            inserted_count += 1
            if inserted_count <= 5:
                print(f"  Inserted: {category} - {date}")
        else:
            skipped_count += 1

    if inserted_count > 5:
        print(f"  ... and {inserted_count - 5} more")

    conn.commit()
    cursor.close()

    print(f"\n=== BLS {file_type.title()} Upload Summary ===")
    print(f"Total records in CSV: {len(df)}")
    print(f"Records inserted: {inserted_count}")
    print(f"Records skipped (duplicates/invalid): {skipped_count}")

def upload_trends_data(conn):
    """Upload Google Trends data from CSV to database"""
    data_dir = get_data_dir('disc_spending')
    file_path = str(data_dir / 'discretionary_trends_summary.csv')

    df = pd.read_csv(file_path)
    print(f"\nLoaded {len(df)} Trends records from {file_path}")

    cursor = conn.cursor()
    inserted_count = 0
    updated_count = 0
    skipped_count = 0

    print("\nUploading Google Trends data...")
    for _, row in df.iterrows():
        category = row.get('Category')
        keyword = row.get('Keyword')
        avg_interest = row.get('Avg Interest')
        rank = row.get('Rank in Cat')

        if pd.isna(category) or pd.isna(keyword):
            skipped_count += 1
            continue

        # Convert NaN to None for SQL NULL
        avg_interest = None if pd.isna(avg_interest) else avg_interest
        rank = None if pd.isna(rank) else int(rank)

        cursor.execute(
            "SELECT COUNT(*) FROM TRENDS_DATA WHERE CATEGORY = %s AND KEYWORD = %s",
            (category, keyword)
        )
        if cursor.fetchone()[0] == 0:
            cursor.execute("""
                INSERT INTO TRENDS_DATA (CATEGORY, KEYWORD, AVG_INTEREST, RANK_IN_CAT, LAST_UPDATED)
                VALUES (%s, %s, %s, %s, NOW())
            """, (category, keyword, avg_interest, rank))
            inserted_count += 1
            if inserted_count <= 5:
                print(f"  Inserted: {category} - {keyword}")
        else:
            cursor.execute("""
                UPDATE TRENDS_DATA
                SET AVG_INTEREST = %s, RANK_IN_CAT = %s, LAST_UPDATED = NOW()
                WHERE CATEGORY = %s AND KEYWORD = %s
            """, (avg_interest, rank, category, keyword))
            updated_count += 1

    if inserted_count > 5:
        print(f"  ... and {inserted_count - 5} more")

    conn.commit()
    cursor.close()

    print(f"\n=== Trends Upload Summary ===")
    print(f"Total records in CSV: {len(df)}")
    print(f"Records inserted: {inserted_count}")
    print(f"Records updated: {updated_count}")
    print(f"Records skipped (invalid): {skipped_count}")

def main():
    """Main upload process"""
    conn = connect_database()
    if not conn:
        return

    try:
        print("\n" + "=" * 70)
        print("DISCRETIONARY SPENDING DATA UPLOADER")
        print("=" * 70)

        # Check sync status
        bls_summary_sync = check_bls_sync(conn, 'summary')
        bls_monthly_sync = check_bls_sync(conn, 'monthly')
        trends_sync = check_trends_sync(conn)

        if bls_summary_sync['is_synced'] and bls_monthly_sync['is_synced'] and trends_sync['is_synced']:
            print("\nAll data is up to date. Nothing to upload.")
            return

        # Upload BLS summary data if needed
        if not bls_summary_sync['is_synced']:
            print(f"\n{bls_summary_sync['missing_count']} BLS summary record(s) need to be uploaded.")
            proceed = input("Upload BLS CPI summary data? (y/n): ").strip().lower()
            if proceed == 'y':
                upload_bls_data(conn, 'summary')

        # Upload BLS monthly data if needed
        if not bls_monthly_sync['is_synced']:
            print(f"\n{bls_monthly_sync['missing_count']} BLS monthly record(s) need to be uploaded.")
            proceed = input("Upload BLS CPI monthly data? (y/n): ").strip().lower()
            if proceed == 'y':
                upload_bls_data(conn, 'monthly')

        # Upload Trends data if needed
        if not trends_sync['is_synced']:
            print(f"\n{trends_sync['missing_count']} Trends record(s) need to be uploaded/updated.")
            proceed = input("Upload Google Trends data? (y/n): ").strip().lower()
            if proceed == 'y':
                upload_trends_data(conn)

        print("\nUpload process complete!")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        if conn and conn.is_connected():
            conn.close()
            print("\nDatabase connection closed")

if __name__ == "__main__":
    main()
