#!/usr/bin/env python3
"""
Automated scraping pipeline - runs run.py every 12 hours
"""

import time
import subprocess
from datetime import datetime, timedelta

# Configuration
RUN_INTERVAL_HOURS = 12

def run_pipeline():
    """Run the run.py script"""
    print("=" * 70)
    print(f"Starting run.py at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    print()

    try:
        subprocess.run(["python", "run.py"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"\nError running pipeline: {e}")
    except KeyboardInterrupt:
        raise

def main():
    """Main loop - runs pipeline every 12 hours"""
    print("\n" + "=" * 70)
    print("AUTOMATED SCRAPER - CONTINUOUS MODE")
    print(f"Running every {RUN_INTERVAL_HOURS} hours")
    print("Press Ctrl+C to stop")
    print("=" * 70 + "\n")

    run_count = 0

    try:
        while True:
            run_count += 1
            print(f"\n{'#' * 70}")
            print(f"RUN #{run_count}")
            print(f"{'#' * 70}\n")

            # Run the pipeline
            run_pipeline()

            # Calculate next run time
            next_run = datetime.now() + timedelta(hours=RUN_INTERVAL_HOURS)
            print(f"\n{'=' * 70}")
            print(f"Next run scheduled at: {next_run.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"Sleeping for {RUN_INTERVAL_HOURS} hours...")
            print(f"{'=' * 70}\n")

            # Sleep for specified interval
            time.sleep(RUN_INTERVAL_HOURS * 3600)

    except KeyboardInterrupt:
        print("\n\n" + "=" * 70)
        print("Stopped by user (Ctrl+C)")
        print(f"Total runs completed: {run_count}")
        print(f"Exited at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 70)

if __name__ == "__main__":
    main()
