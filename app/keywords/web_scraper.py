import sys
from pathlib import Path

# adding project root to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import requests
from bs4 import BeautifulSoup
import json
import time
from datetime import datetime

# imports and preproecessing
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from app.shared_utils import parse_publish_date, create_chrome_options, get_data_dir
from tools.keyword_extractor import add_keywords_to_articles
from tools.sentiment_analyzer import add_sentiment_to_articles
from tools.db_uploader import DatabaseUploader

# list of HTML page URLs to scrape
#  *+* Be mindful of HTML layout before scraping *+*
HTML_URLS = [
    "https://www.housebeautiful.com/room-decorating/",
    "https://www.apartmenttherapy.com/collection/ideas-inspiration/",
    "https://www.remodelista.com/get-inspired",
    " https://www.elledecor.com/home-remodeling-renovating/"
    # Add more HTML page URLs here
]

def extract_publish_date_from_html(soup):
    """Try to extract publish date from HTML article page"""
    date_selectors = [
        ('meta', {'property': 'article:published_time'}),
        ('meta', {'name': 'pubdate'}),
        ('meta', {'name': 'publishdate'}),
        ('meta', {'property': 'og:published_time'}),
        ('time', {'class': 'published'}),
        ('time', {'datetime': True}),
        ('span', {'class': 'date'}),
        ('span', {'class': 'publish-date'}),
    ]
    
    for tag_name, attrs in date_selectors:
        element = soup.find(tag_name, attrs)
        if element:
            date_str = (element.get('content') or 
                       element.get('datetime') or 
                       element.get_text().strip())
            if date_str:
                parsed = parse_publish_date(date_str)
                if parsed:
                    return parsed
    
    return None

def get_article_links_from_page(page_url):
    """Extract all article links from the main page using Selenium"""
    print(f"Fetching page: {page_url}")

    chrome_options = create_chrome_options()

    try:
        driver = webdriver.Chrome(options=chrome_options)
        driver.get(page_url)
        
        # Wait for links to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "a"))
        )
        time.sleep(3)  # Extra wait for dynamic content
        
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        driver.quit()
        
        articles = []
        
        # Get base domain from page_url
        from urllib.parse import urlparse
        parsed = urlparse(page_url)
        base_domain = f"{parsed.scheme}://{parsed.netloc}"
        base_path = parsed.path.rstrip('/')
        
        # Look for <a> tags with href containing article paths
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href']
            # Filter for actual article URLs
            if base_path in href and href.count('/') >= 4:
                # Make absolute URL if needed
                if href.startswith('http'):
                    full_url = href
                elif href.startswith('/'):
                    full_url = base_domain + href
                else:
                    continue
                
                # Get title
                title = a_tag.get_text().strip()
                if not title:
                    heading = a_tag.find(['h1', 'h2', 'h3', 'h4'])
                    title = heading.get_text().strip() if heading else 'No title'
                
                # Avoid duplicates
                if full_url not in [art['link'] for art in articles]:
                    articles.append({
                        'link': full_url,
                        'title': title,
                        'description': '',
                        'published_date': None,
                        'source': page_url,
                        'paragraphs': []
                    })
        
        print(f"Found {len(articles)} unique article links")
        
        # Show first 5 links as sample
        for i, article in enumerate(articles[:5]):
            print(f"\n  Article {i+1}:")
            print(f"    Title: {article['title'][:60]}...")
            print(f"    Link: {article['link']}")
        
        return articles
        
    except Exception as e:
        print(f"Error fetching page: {str(e)}")
        if 'driver' in locals():
            driver.quit()
        return []

def get_existing_articles_from_db(uploader):
    """Get set of existing articles from database (title, published_date)"""
    try:
        cursor = uploader.connection.cursor(dictionary=True)
        cursor.execute("SELECT TITLE, PUBLISHED_DATE FROM ARTICLES")
        db_articles = cursor.fetchall()
        cursor.close()

        # Create set of (title, date) tuples for fast lookup
        existing = set()
        for article in db_articles:
            title = article.get('TITLE', '').strip()
            pub_date = str(article.get('PUBLISHED_DATE')) if article.get('PUBLISHED_DATE') else None
            existing.add((title, pub_date))

        return existing
    except Exception as e:
        print(f"Warning: Could not check database for existing articles: {e}")
        return set()

def scrape_paragraphs_from_article(article_url, article_data):
    """Scrape all <p> tags from an article page using Selenium"""
    print(f"  Scraping: {article_url}")

    chrome_options = create_chrome_options()

    try:
        # applying web driver with Chrome options for 
        #   maximum compatability
        driver = webdriver.Chrome(options=chrome_options)
        driver.get(article_url)
        
        WebDriverWait(driver, 10).until( # wait for content to load
            EC.presence_of_element_located((By.TAG_NAME, "p"))
        )
        time.sleep(2)
        
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        driver.quit()
        # close out driver after it has finished
        
        # Extract publish date
        publish_date = extract_publish_date_from_html(soup)
        if publish_date:
            article_data['published_date'] = publish_date # look for published date tag
            print(f"    Published: {publish_date}")
        
        # Find all <p> tags

        # use .find_all() to look for any p tags within the 
        p_tags = soup.find_all('p')
        
        # Extract text from paragraphs
        paragraphs = []
        for p in p_tags:
            text = p.get_text().strip()
            # Filter out JavaScript warnings and short paragraphs
            if text and len(text) > 20 and 'enable JavaScript' not in text:
                paragraphs.append(text)
        
        print(f"    Found {len(paragraphs)} paragraphs") # return the # of paragraphs found
        return paragraphs
        
    except Exception as e:
        print(f"    Error: {str(e)}")
        if 'driver' in locals():
            driver.quit() # close out driver after it has finished
        return []

def main():
    print("=" * 70)
    print("Multi-HTML Article Scraper (Selenium)")
    print("=" * 70)
    
    all_articles = []
    
    # Step 1: Get all article links from ALL HTML pages
    for page_url in HTML_URLS:
        print(f"\n{'='*70}")
        print(f"Processing page: {page_url}")
        print(f"{'='*70}")
        
        articles = get_article_links_from_page(page_url)
        all_articles.extend(articles)
        
        time.sleep(2)
    
    if not all_articles:
        print("\nNo articles found. Exiting.")
        return

    # Step 2: Check database for existing articles
    print(f"\n{'*+'*70}")
    print("Checking database for existing articles...")
    print(f"{'*+*'*70}")

    uploader = DatabaseUploader()
    existing_articles = set()

    if uploader.connect():
        existing_articles = get_existing_articles_from_db(uploader)
        print(f"Found {len(existing_articles)} existing articles in database")
        uploader.close()
    else:
        print("WARNING: Could not connect to database. Proceeding without duplicate checking.")

    # CHECKING FOR EXISTING ARTICLES
    # Filter out articles that already exist (matching by title only, since we don't have published_date yet)
    # We'll check the full title+date match after scraping the publish date
    existing_titles = {title for title, date in existing_articles}

    articles_to_scrape = []
    skipped_by_title = []

    for article in all_articles:
        title = article.get('title', '').strip()
        if title in existing_titles:
            skipped_by_title.append(article)
        else:
            articles_to_scrape.append(article)

    # print found articles
    print(f"\nArticles found: {len(all_articles)}")
    print(f"Already in database (by title): {len(skipped_by_title)}")
    print(f"New articles to scrape: {len(articles_to_scrape)}")

    if not articles_to_scrape:
        print("\nNo new articles to scrape. All articles already exist in database.")
        return

    # Step 3: Ask if user wants to scrape the articles
    print(f"\n{'='*70}")
    scrape = input("Scrape paragraphs from new articles? (y/n): ").strip().lower()

    if scrape != 'y':
        print("Exiting without scraping.")
        return
    
    # Step 4: Scrape paragraphs from each article
    print(f"\nScraping {len(articles_to_scrape)} new articles...")
    print("-" * 70)

    for i, article in enumerate(articles_to_scrape, 1):
        print(f"\n[{i}/{len(articles_to_scrape)}] {article['title'][:50]}...")
        paragraphs = scrape_paragraphs_from_article(article['link'], article)
        # call paragraphs srcapped on line 184
        article['paragraphs'] = paragraphs

        time.sleep(3)  # Longer delay for Selenium

    # KEYWORD EXTRACTOR AND SENTIMENT ANALYZER
    # Step 5: Extract keywords from new articles
    print("\n" + "-" * 70)
    print("Extracting keywords...")
    add_keywords_to_articles(articles_to_scrape, num_keywords=15, verbose=True)

    # Step 5.5: Analyze entity sentiment
    print("\n" + "-" * 70)
    print("Analyzing entity sentiment...")
    add_sentiment_to_articles(articles_to_scrape, top_n=10, verbose=True)

    # SAVED TO JSON BEFORE DB UPLOAD
    # Step 6: Save results to JSON
    data_dir = get_data_dir('keywords')
    output_file = data_dir / f"html_articles_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    with open(output_file, 'w', encoding='utf-8') as f: # dump scraped articles
        json.dump(articles_to_scrape, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 70)
    print(f"✓ Done! Scraped {len(articles_to_scrape)} new articles from {len(HTML_URLS)} page(s)")

    # print out a summary of statistics after run
    total_paragraphs = sum(len(a['paragraphs']) for a in articles_to_scrape)
    successful_content = sum(1 for a in articles_to_scrape if len(a['paragraphs']) > 0)
    successful_keywords = sum(1 for a in articles_to_scrape if a.get('keywords'))
    successful_sentiment = sum(1 for a in articles_to_scrape if a.get('entity_sentiment'))
    articles_with_dates = sum(1 for a in articles_to_scrape if a.get('published_date'))

    print(f"  - {successful_content} articles with content")
    print(f"  - {total_paragraphs} total paragraphs extracted")
    print(f"  - {successful_keywords} articles with keywords")
    print(f"  - {successful_sentiment} articles with entity sentiment")
    print(f"  - {articles_with_dates} articles with publish dates")
    print(f"  - {len(skipped_by_title)} articles skipped (already in database)")
    print(f"  - Saved to: {output_file}")
    print("=" * 70)

if __name__ == "__main__":
    main()