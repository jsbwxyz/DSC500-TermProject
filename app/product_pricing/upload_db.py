"""
Product Pricing Database Uploader
Uploads Amazon price history to PRICE_HISTORY table
"""

import sys
from pathlib import Path

# Add project root to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import json
import os
import mysql.connector
from datetime import datetime
from app.shared_utils import connect_database, get_data_dir

def check_sync(conn):
    """Check if database is synced with local JSON file"""
    print("=" * 70)
    print("Checking product pricing sync status...")
    print("=" * 70)

    data_dir = get_data_dir('product_pricing')
    file_path = str(data_dir / 'all_prices.json')

    if not os.path.exists(file_path):
        print(f"\nNo data file found at {file_path}")
        return {'is_synced': True, 'missing_count': 0}

    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
        file_entries = data.get("data", [])
    except Exception as e:
        print(f"Error reading data file: {e}")
        return {'is_synced': False, 'missing_count': 0}

    print(f"\nFound {len(file_entries)} price entries in JSON file")

    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM PRICE_HISTORY")
    db_count = cursor.fetchone()[0]
    print(f"Found {db_count} price entries in database")

    # Check for missing entries
    missing_count = 0
    for entry in file_entries:
        asin = entry.get("asin")
        timestamp_str = entry.get("timestamp")

        if not (asin and timestamp_str):
            continue

        timestamp = datetime.fromisoformat(timestamp_str)

        cursor.execute(
            "SELECT COUNT(*) FROM PRICE_HISTORY WHERE ASIN = %s AND TIMESTAMP = %s",
            (asin, timestamp)
        )
        if cursor.fetchone()[0] == 0:
            missing_count += 1

    cursor.close()

    print("\n" + "=" * 70)
    if missing_count == 0:
        print("✓ Price database is UP TO DATE")
    else:
        print(f"⚠ {missing_count} price entry(ies) need to be uploaded")
    print("=" * 70)

    return {'is_synced': missing_count == 0, 'missing_count': missing_count}

def upload_prices(conn):
    """Upload price data from JSON to database"""
    cursor = conn.cursor()
    data_dir = get_data_dir('product_pricing')
    file_path = str(data_dir / 'all_prices.json')

    with open(file_path, 'r') as f:
        data = json.load(f)

    entries = data.get("data", [])
    inserted_count = 0
    skipped_count = 0

    print("\nUploading price entries...")
    for entry in entries:
        asin = entry.get("asin")
        price = entry.get("price")
        raw_price = entry.get("raw_price", "")
        timestamp_str = entry.get("timestamp")

        if not (asin and price and timestamp_str):
            skipped_count += 1
            continue

        timestamp = datetime.fromisoformat(timestamp_str)

        cursor.execute(
            "SELECT COUNT(*) FROM PRICE_HISTORY WHERE ASIN = %s AND TIMESTAMP = %s",
            (asin, timestamp)
        )
        if cursor.fetchone()[0] == 0:
            cursor.execute(
                "INSERT INTO PRICE_HISTORY (ASIN, PRICE, RAW_PRICE, TIMESTAMP) VALUES (%s, %s, %s, %s)",
                (asin, price, raw_price, timestamp)
            )
            inserted_count += 1
            if inserted_count <= 5:
                print(f"  Inserted: ASIN {asin}, Price {price}, Time {timestamp}")
        else:
            skipped_count += 1

    if inserted_count > 5:
        print(f"  ... and {inserted_count - 5} more")

    conn.commit()
    cursor.close()

    print(f"\n=== Upload Summary ===")
    print(f"Total entries in JSON: {len(entries)}")
    print(f"Entries inserted: {inserted_count}")
    print(f"Entries skipped (duplicates/invalid): {skipped_count}")

def main():
    """Main upload process"""
    conn = connect_database()
    if not conn:
        return

    try:
        sync_status = check_sync(conn)

        if not sync_status['is_synced']:
            proceed = input(f"\nUpload {sync_status['missing_count']} missing price entries? (y/n): ").strip().lower()
            if proceed == 'y':
                upload_prices(conn)
                print("\nUpload complete!")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if conn and conn.is_connected():
            conn.close()
            print("\nDatabase connection closed")

if __name__ == "__main__":
    main()
