import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
from app.shared_utils import create_chrome_options, get_standard_headers, get_data_dir

# Import scraper modules
import web_scraper
import rss_scraper

DATA_DIR = get_data_dir('article_keywords')

def load_existing_articles():
    """Load all existing articles from JSON files in /data directory"""
    existing_links = set()
    existing_files = []

    if not DATA_DIR.exists():
        DATA_DIR.mkdir(exist_ok=True)
        return existing_links, existing_files

    for json_file in DATA_DIR.glob("*.json"):
        existing_files.append(json_file.name)
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                articles = json.load(f)
                for article in articles:
                    if 'link' in article:
                        existing_links.add(article['link'])
        except Exception as e:
            print(f"Warning: Could not read {json_file}: {e}")

    return existing_links, existing_files

def get_article_links_from_html_source(page_url):
    """Get article links from HTML page without full scraping"""
    print(f"  Checking: {page_url}")

    chrome_options = create_chrome_options()

    try:
        driver = webdriver.Chrome(options=chrome_options)
        driver.get(page_url)

        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "a"))
        )
        time.sleep(3)

        soup = BeautifulSoup(driver.page_source, 'html.parser')
        driver.quit()

        from urllib.parse import urlparse
        parsed = urlparse(page_url)
        base_domain = f"{parsed.scheme}://{parsed.netloc}"
        base_path = parsed.path.rstrip('/')

        links = set()
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href']
            if base_path in href and href.count('/') >= 4:
                if href.startswith('http'):
                    links.add(href)
                elif href.startswith('/'):
                    links.add(base_domain + href)

        return links

    except Exception as e:
        print(f"    Error: {e}")
        if 'driver' in locals():
            driver.quit()
        return set()

def get_article_links_from_rss_source(rss_url):
    """Get article links from RSS feed without full scraping"""
    print(f"  Checking: {rss_url}")

    headers = get_standard_headers()

    try:
        response = requests.get(rss_url, headers=headers, timeout=15)

        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'lxml-xml')
            items = soup.find_all('item')

            links = set()
            for item in items:
                link_tag = item.find('link')
                if link_tag and link_tag.text.strip():
                    links.add(link_tag.text.strip())

            return links
        else:
            print(f"    Failed: status {response.status_code}")
            return set()

    except Exception as e:
        print(f"    Error: {e}")
        return set()

def check_for_new_articles():
    """Check if there are new articles available from sources"""
    print("=" * 70)
    print("Checking for new articles...")
    print("=" * 70)

    # Load existing articles
    existing_links, existing_files = load_existing_articles()
    print(f"\nFound {len(existing_files)} existing data file(s) with {len(existing_links)} articles")
    if existing_files:
        print("Existing files:")
        for f in existing_files:
            print(f"  - {f}")

    # Check HTML sources
    print(f"\nChecking {len(web_scraper.HTML_URLS)} HTML source(s)...")
    html_links = set()
    for url in web_scraper.HTML_URLS:
        links = get_article_links_from_html_source(url)
        html_links.update(links)
        print(f"    Found {len(links)} article links")
        time.sleep(2)

    # Check RSS sources
    print(f"\nChecking {len(rss_scraper.RSS_URLS)} RSS source(s)...")
    rss_links = set()
    for url in rss_scraper.RSS_URLS:
        links = get_article_links_from_rss_source(url)
        rss_links.update(links)
        print(f"    Found {len(links)} article links")
        time.sleep(2)

    # Combine all available links
    all_available_links = html_links.union(rss_links)

    # Find new links
    new_links = all_available_links - existing_links

    print("\n" + "=" * 70)
    print("Summary:")
    print(f"  - Total available articles: {len(all_available_links)}")
    print(f"  - Already scraped: {len(existing_links)}")
    print(f"  - New articles: {len(new_links)}")
    print("=" * 70)

    return new_links, html_links, rss_links

def main():
    # Check for new articles
    new_links, html_links, rss_links = check_for_new_articles()

    if len(new_links) == 0:
        print("\nNo new articles found. All sources are up to date.")
        print("Nothing to retrieve.")
        return

    print(f"\nFound {len(new_links)} new article(s) to scrape.")
    print("\nSample new articles:")
    for i, link in enumerate(list(new_links)[:5], 1):
        print(f"  {i}. {link}")

    proceed = input("\nProceed with scraping? (y/n): ").strip().lower()

    if proceed != 'y':
        print("Exiting without scraping.")
        return

    # Run appropriate scrapers
    print("\n" + "=" * 70)
    print("Starting scraping process...")
    print("=" * 70)

    # Check if we need to run web scraper
    new_html_links = new_links.intersection(html_links)
    if new_html_links:
        print(f"\nRunning web scraper for {len(new_html_links)} new HTML articles...")
        web_scraper.main()

    # Check if we need to run RSS scraper
    new_rss_links = new_links.intersection(rss_links)
    if new_rss_links:
        print(f"\nRunning RSS scraper for {len(new_rss_links)} new RSS articles...")
        rss_scraper.main()

    print("\n" + "=" * 70)
    print("Scraping complete!")
    print("=" * 70)

if __name__ == "__main__":
    main()
