import sys
from pathlib import Path

# Add project root to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import requests
from bs4 import BeautifulSoup
import json
import time
from datetime import datetime
from app.shared_utils import parse_publish_date, get_standard_headers, get_data_dir
from pipeline.keyword_extractor import add_keywords_to_articles

# List of RSS feed URLs
RSS_URLS = [
    "apartmenttherapy.com/main.rss"
    # Add more RSS URLs here
]

def get_article_links_from_rss(rss_url):
    """Extract all article links from the RSS feed"""
    print(f"Fetching RSS feed: {rss_url}")

    headers = get_standard_headers()

    try:
        response = requests.get(rss_url, headers=headers, timeout=15)
        print(f"Status code: {response.status_code}")
        
        if response.status_code == 200:
            # Parse the XML with BeautifulSoup using lxml parser
            soup = BeautifulSoup(response.content, 'lxml-xml')
            
            # Find all <item> tags
            items = soup.find_all('item')
            print(f"Found {len(items)} items in RSS feed")
            
            articles = []
            for item in items:
                # Extract link, title, and other metadata
                link_tag = item.find('link')
                title_tag = item.find('title')
                desc_tag = item.find('description')
                pub_tag = item.find('pubDate')
                
                if link_tag and link_tag.text.strip():
                    pub_date_str = pub_tag.text.strip() if pub_tag else None
                    
                    article = {
                        'link': link_tag.text.strip(),
                        'title': title_tag.text.strip() if title_tag else 'No title',
                        'description': desc_tag.text.strip() if desc_tag else '',
                        'published': pub_date_str,
                        'published_date': parse_publish_date(pub_date_str),  # Parsed datetime
                        'source': rss_url,
                        'paragraphs': []
                    }
                    articles.append(article)
            
            print(f"Extracted {len(articles)} article links")
            
            # Show first 3 links as sample
            for i, article in enumerate(articles[:3]):
                print(f"\n  Article {i+1}:")
                print(f"    Title: {article['title'][:60]}...")
                print(f"    Link: {article['link']}")
                print(f"    Published: {article['published_date'] or 'Unknown'}")
            
            return articles
        else:
            print(f"Failed to fetch RSS feed: {response.status_code}")
            return []
            
    except Exception as e:
        print(f"Error fetching RSS feed: {str(e)}")
        return []

def scrape_paragraphs_from_article(article_url):
    """Scrape all <p> tags from an article page"""
    print(f"  Scraping: {article_url}")

    headers = get_standard_headers()

    try:
        response = requests.get(article_url, headers=headers, timeout=15)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find all <p> tags
            p_tags = soup.find_all('p')
            
            # Extract text from each paragraph
            paragraphs = []
            for p in p_tags:
                text = p.get_text().strip()
                # Filter out very short paragraphs (navigation, etc.)
                if text and len(text) > 20:
                    paragraphs.append(text)
            
            print(f"    Found {len(paragraphs)} paragraphs")
            return paragraphs
        else:
            print(f"    Failed: status {response.status_code}")
            return []
            
    except Exception as e:
        print(f"    Error: {str(e)}")
        return []

def main():
    print("=" * 70)
    print("Multi-RSS Article Scraper")
    print("=" * 70)
    
    all_articles = []
    
    # Step 1: Get all article links from ALL RSS feeds
    for rss_url in RSS_URLS:
        print(f"\n{'='*70}")
        print(f"Processing RSS feed: {rss_url}")
        print(f"{'='*70}")
        
        articles = get_article_links_from_rss(rss_url)
        all_articles.extend(articles)
        
        # Brief pause between RSS feeds
        time.sleep(2)
    
    if not all_articles:
        print("\nNo articles found. Exiting.")
        return
    
    # Step 2: Ask if user wants to scrape the articles
    print(f"\n{'='*70}")
    print(f"Total: {len(all_articles)} articles found from {len(RSS_URLS)} RSS feed(s).")
    scrape = input("Scrape paragraphs from all articles? (y/n): ").strip().lower()
    
    if scrape != 'y':
        print("Exiting without scraping.")
        return
    
    # Step 3: Scrape paragraphs from each article
    print(f"\nScraping {len(all_articles)} articles...")
    print("-" * 70)
    
    for i, article in enumerate(all_articles, 1):
        print(f"\n[{i}/{len(all_articles)}] {article['title'][:50]}...")
        paragraphs = scrape_paragraphs_from_article(article['link'])
        article['paragraphs'] = paragraphs
        
        # Be respectful to the server
        time.sleep(1)
    
    # Step 4: Extract keywords from all articles
    print("\n" + "-" * 70)
    add_keywords_to_articles(all_articles, num_keywords=15, verbose=True)
    
    # Step 5: Save results to JSON
    data_dir = get_data_dir('keywords')
    output_file = data_dir / f"rss_articles_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_articles, f, indent=2, ensure_ascii=False)
    
    print("\n" + "=" * 70)
    print(f"✓ Done! Scraped {len(all_articles)} articles from {len(RSS_URLS)} RSS feed(s)")
    
    # Summary stats
    total_paragraphs = sum(len(a['paragraphs']) for a in all_articles)
    successful_content = sum(1 for a in all_articles if len(a['paragraphs']) > 0)
    successful_keywords = sum(1 for a in all_articles if a.get('keywords'))
    articles_with_dates = sum(1 for a in all_articles if a.get('published_date'))
    
    print(f"  - {successful_content} articles with content")
    print(f"  - {total_paragraphs} total paragraphs extracted")
    print(f"  - {successful_keywords} articles with keywords")
    print(f"  - {articles_with_dates} articles with publish dates")
    print(f"  - Saved to: {output_file}")
    print("=" * 70)

if __name__ == "__main__":
    main()