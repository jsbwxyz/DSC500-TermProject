# run.py
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
import json
import datetime
import os
import time
import sys

options = Options()
options.add_argument("--headless")
options.add_argument("--disable-gpu")
options.add_argument("--no-sandbox")

asins = [
    'B08573DQ39', 'B0C3VQ8B5W', 'B09XHWKXP4', 'B0D41GF9CT',
    'B07NQJ4XM6', 'B0F2M35CR8', 'B00CQGTGZQ', 'B08HV56P6N',
    'B0D1CFZ5L8', 'B078MMPWZX', 'B0BV23YTHV', 'B0DHXDDQK3',
    'B09K5927B5', 'B0DB8F7GDN', 'B0BWTT3WK1', 'B0CC51YJQF',
    'B0C2V9THZD', 'B0DZ6SP7PJ', 'B0CDGL2J8R', 'B0D3V34FN1',
    'B0BTPGFTYD', 'B0CPDXMWN8', 'B0D7BTL3B5', 'B0C77GP9XB',
    'B08YJPZY9P', 'B0B39M5WHC', 'B086ZLGLV3', 'B0BR5JHB3Z',
    'B0C4SZBN64', 'B0CPC1NCZS', 'B07FXDS1DD', 'B0CZ8P1VJV',
    'B09DKH8XDS', 'B0CC27124P', 'B0928RRR2Y', 'B091JXDLDX',
    'B0BPR2SVD9', 'B00KH9PR48', 'B07KDXVMBZ', 'B0DHSNVD1Q',
    'B0DHRWGGRB', 'B0D9YFNQCC', 'B09TN4MP6V', 'B0DSP674SK',
    'B09JBCSC7H', 'B0BC1GS34Q', 'B0BWYVNYW1'
]

driver = None

def setup_driver():
    global driver
    if driver is None:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)

def get_amazon_price(asin):
    global driver
    setup_driver()
    url = f"https://www.amazon.com/dp/{asin}"
    try:
        driver.get(url)
        price_element = driver.find_element(By.CLASS_NAME, "a-price")
        price = price_element.text.replace("\n", ".")
        return price
    except Exception as e:
        print(f"Error fetching price for ASIN {asin}: {e}")
        return None

def retry_scrape_with_backoff(asin):
    for _ in range(3):
        price = get_amazon_price(asin)
        if price:
            return price
        time.sleep(5)
    time.sleep(300)
    for _ in range(3):
        price = get_amazon_price(asin)
        if price:
            return price
        time.sleep(5)
    return None

def save_all_to_json(all_data, output_file='data/all_prices.json'):
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    timestamp = datetime.datetime.now().isoformat()
    output = {
        "timestamp": timestamp,
        "data": all_data
    }
    if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
        try:
            with open(output_file, 'r') as f:
                existing_data = json.load(f)
            if "data" in existing_data and isinstance(existing_data["data"], list):
                existing_data["data"].extend(all_data)
                existing_data["timestamp"] = timestamp
                output = existing_data
        except json.JSONDecodeError:
            pass
    with open(output_file, 'w') as f:
        json.dump(output, f, indent=2)

def run_scrape_single(asin):
    global driver
    setup_driver()
    price = retry_scrape_with_backoff(asin)
    if price:
        try:
            price_float = float(price.replace('$', '').replace('€', '').replace('£', ''))
            data = [{
                "asin": asin,
                "timestamp": datetime.datetime.now().isoformat(),
                "price": price_float,
                "raw_price": price
            }]
            save_all_to_json(data)
            print(f"[{asin}] Price: {price}")
            return price_float
        except ValueError:
            print(f"[{asin}] Invalid price format: {price}")
            return None
    else:
        print(f"[{asin}] Failed to retrieve price")
        return None

def close_driver():
    global driver
    if driver:
        driver.quit()
        driver = None

if __name__ == "__main__":
    if len(sys.argv) > 1:
        # User specified an ASIN directly: python3 run.py B08573DQ39
        asin = sys.argv[1].strip().upper()
        price = run_scrape_single(asin)
        if price:
            print(f"Current price for {asin}: ${price}")
        close_driver()
    else:
        # No argument — run through timing scheduler as normal
        from tools.timing import main as timing_main
        timing_main()