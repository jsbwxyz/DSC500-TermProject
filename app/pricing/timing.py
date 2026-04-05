# timing.py
import random
import time
import threading
from datetime import datetime, timedelta
from main import run_scrape_single  # Calls single-ASIN scrape

# Time window ranges
WINDOWS = {
    "morning": (6, 9),
    "noon": (11, 13),
    "evening": (17, 20),
    "overnight": (0, 3)
}

def get_random_time_in_window(start_hour, end_hour):
    now = datetime.now()
    hour = random.randint(start_hour, end_hour - 1)
    minute = random.randint(0, 59)
    second = random.randint(0, 59)
    scheduled_time = now.replace(hour=hour, minute=minute, second=second, microsecond=0)
    if scheduled_time < now:
        scheduled_time += timedelta(days=1)
    return scheduled_time

def countdown(seconds, label):
    while seconds > 0:
        hrs, rem = divmod(seconds, 3600)
        mins, secs = divmod(rem, 60)
        HIGHLIGHT = '\033[1;33m'
        RESET = '\033[0m'
        print(f"{HIGHLIGHT}[{label}] Next run in {int(hrs)}h {int(mins)}m {int(secs)}s{RESET}", end='\r')
        time.sleep(3)
        seconds -= 3
    print()

def schedule_asin_run(window_name, start_hour, end_hour, asin):
    def run():
        while True:
            now = datetime.now()
            target_time = get_random_time_in_window(start_hour, end_hour)
            sleep_seconds = int((target_time - now).total_seconds())
            print(f"[{window_name}] ASIN {asin} scheduled at {target_time.strftime('%Y-%m-%d %H:%M:%S')}")
            if sleep_seconds > 0:
                countdown(sleep_seconds, f"{window_name} - {asin}")
            run_scrape_single(asin)
    threading.Thread(target=run, daemon=True).start()

def main():
    from main import asins  # Imported here to prevent circular import
    for window_name, (start_hour, end_hour) in WINDOWS.items():
        for asin in set(asins):  # Deduplicate
            schedule_asin_run(window_name, start_hour, end_hour, asin)
    while True:
        time.sleep(60)

if __name__ == "__main__":
    main()
