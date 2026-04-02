"""
Unified Database Upload Orchestrator
Delegates to individual upload scripts in each data source directory
"""

import sys
import os
import subprocess
from pathlib import Path
from app.shared_utils import get_db_config

def run_script(script_path, description):
    """Run a Python script in its directory and return success status"""
    script_path = Path(script_path)

    if not script_path.exists():
        print(f"Error: Script not found - {script_path}")
        return False

    print(f"\n{'=' * 70}")
    print(f"Running: {description}")
    print(f"{'=' * 70}\n")

    # Run script in its own directory
    original_dir = os.getcwd()
    try:
        os.chdir(script_path.parent)
        result = subprocess.run([sys.executable, script_path.name], check=False)
        os.chdir(original_dir)
        return result.returncode == 0
    except Exception as e:
        print(f"Error running {script_path}: {e}")
        os.chdir(original_dir)
        return False

def sync_all():
    """Check sync status for all data sources"""
    print("\n" + "=" * 70)
    print("CHECKING SYNC STATUS FOR ALL DATA SOURCES")
    print("=" * 70)

    # Article keywords sync
    print("\n[1/3] Article Keywords")
    print("-" * 70)
    subprocess.run([sys.executable, '-c', """
from db_uploader import DatabaseUploader
uploader = DatabaseUploader()  # Uses app.shared_utils config now
if uploader.connect():
    uploader.check_sync()
    uploader.close()
"""], cwd='app/article_keywords/tools')

    # Product pricing sync
    print("\n[2/3] Product Pricing")
    print("-" * 70)
    subprocess.run([sys.executable, '-c', """
import upload_db
conn = upload_db.connect_database()  # Uses app.shared_utils now
if conn:
    upload_db.check_sync(conn)
    conn.close()
"""], cwd='app/product_pricing')

    # Discretionary spending sync
    print("\n[3/3] Discretionary Spending")
    print("-" * 70)
    subprocess.run([sys.executable, '-c', """
import upload_db
conn = upload_db.connect_database()  # Uses app.shared_utils now
if conn:
    upload_db.check_bls_sync(conn, 'summary')
    upload_db.check_bls_sync(conn, 'monthly')
    upload_db.check_trends_sync(conn)
    conn.close()
"""], cwd='app/disc_spending')

    print("\n" + "=" * 70)
    print("SYNC CHECK COMPLETE")
    print("=" * 70)

def upload_articles():
    """Upload article keywords"""
    run_script('app/article_keywords/tools/db_uploader.py', 'Article Keywords Upload')

def upload_prices():
    """Upload product prices"""
    run_script('app/product_pricing/upload_db.py', 'Product Pricing Upload')

def upload_disc_spending():
    """Upload discretionary spending data (interactive)"""
    run_script('app/disc_spending/upload_db.py', 'Discretionary Spending Upload')

def show_help():
    """Show usage instructions"""
    print("""
MTB Data Engine - Unified Database Uploader
==========================================

This script orchestrates uploads by calling individual upload scripts
in each data source directory.

Usage:
    python db_uploader.py <command>

Commands:
    sync                Check sync status for all data sources
    upload-articles     Upload article keywords data
    upload-prices       Upload product pricing data
    upload-disc         Upload discretionary spending data (BLS + Trends)
    help                Show this help message

Examples:
    python db_uploader.py sync
    python db_uploader.py upload-articles
    python db_uploader.py upload-prices

Note: Each data source has its own upload script that can be run directly:
    - app/article_keywords/tools/db_uploader.py
    - app/product_pricing/upload_db.py
    - app/disc_spending/upload_db.py
""")

def main():
    if len(sys.argv) < 2:
        sync_all()
        return

    command = sys.argv[1]

    commands = {
        'sync': sync_all,
        'upload-articles': upload_articles,
        'upload-prices': upload_prices,
        'upload-disc': upload_disc_spending,
        'help': show_help,
        '--help': show_help,
        '-h': show_help,
    }

    if command in commands:
        commands[command]()
    else:
        print(f"Unknown command: {command}")
        print("Run 'python db_uploader.py help' for usage information")
        sys.exit(1)

if __name__ == "__main__":
    main()
