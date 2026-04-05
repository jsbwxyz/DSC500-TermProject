"""
Google Trends Data Fetcher
Fetches Google Trends data for keywords, optionally from database
"""

import time
import pandas as pd
from pytrends.request import TrendReq
import mysql.connector
from mysql.connector import Error
from datetime import datetime, timedelta
import sys
from pathlib import Path

# Add project root to path to import shared utilities
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from app.shared_utils import get_db_config


# Fallback hardcoded keywords per category (used if DB query fails or returns nothing)
FALLBACK_KEYWORDS = {
    "Recreation":             ["fitness tracker", "kayak", "camping gear", "yoga mat", "hiking boots"],
    "Food Away From Home":    ["fast casual dining", "meal kit delivery", "food delivery", "brunch", "omakase"],
    "Apparel":                ["sneakers", "athleisure", "luxury handbag", "vintage clothing", "workwear"],
    "Personal Care":          ["skincare", "hair care", "perfume", "electric toothbrush", "massage gun"],
    "Education":              ["online course", "coding bootcamp", "tutoring", "language learning app", "MBA"],
    "Sporting Goods":         ["pickleball paddle", "golf clubs", "running shoes", "home gym", "bicycle"],
    "Audio / Video":          ["OLED TV", "soundbar", "noise cancelling headphones", "projector", "streaming device"],
    "Pets and Pet Products":  ["dog food", "cat tree", "pet insurance", "dog bed", "pet grooming"],
    "Alcohol Away From Home": ["craft cocktail", "wine bar", "sake", "whiskey tasting", "rooftop bar"],
    "New Vehicles":           ["electric vehicle", "hybrid car", "truck lease", "car deal", "EV incentive"],
}


def get_keywords_from_db(categories: list, months_back: int = 3, limit_per_category: int = 5) -> dict:
    """
    Query keywords from database for articles published in the last N months.

    Args:
        categories: List of BLS category names to match against
        months_back: How many months of articles to look back (default 3)
        limit_per_category: Max keywords per category (default 5)

    Returns:
        Dictionary mapping category names to lists of keywords
    """
    try:
        config = get_db_config()
        connection = mysql.connector.connect(
            host=config['host'],
            user=config['user'],
            password=config['password'],
            database=config['database'],
            port=config['port'],
            charset='utf8mb4'
        )

        cursor = connection.cursor(dictionary=True)

        # Calculate cutoff date
        cutoff_date = datetime.now() - timedelta(days=months_back * 30)
        cutoff_str = cutoff_date.strftime('%Y-%m-%d')

        print(f"\n[DB] Fetching keywords from articles since {cutoff_str}...")

        # Query to get top keywords by frequency from recent articles
        query = """
            SELECT
                k.KEYWORD_TEXT,
                COUNT(DISTINCT a.ARTICLE_ID) as article_count,
                AVG(ak.CONFIDENCE) as avg_confidence
            FROM KEYWORDS k
            JOIN ARTICLE_KEYWORDS ak ON k.KEYWORD_ID = ak.KEYWORD_ID
            JOIN ARTICLES a ON ak.ARTICLE_ID = a.ARTICLE_ID
            WHERE a.PUBLISHED_DATE >= %s
            GROUP BY k.KEYWORD_ID, k.KEYWORD_TEXT
            ORDER BY article_count DESC, avg_confidence DESC
            LIMIT %s
        """

        cursor.execute(query, (cutoff_str, limit_per_category * len(categories)))
        results = cursor.fetchall()

        cursor.close()
        connection.close()

        if not results:
            print(f"  [warn] No keywords found in database for the last {months_back} months")
            return {}

        # Extract keywords and distribute across categories
        # For now, use the same top keywords for all categories
        # In the future, you could categorize keywords based on article content
        top_keywords = [row['KEYWORD_TEXT'] for row in results[:limit_per_category * 2]]

        keywords_map = {}
        for cat in categories:
            # Take a slice of keywords for each category
            keywords_map[cat] = top_keywords[:limit_per_category]

        print(f"  [DB] Found {len(results)} keywords, using top {limit_per_category} per category")

        return keywords_map

    except Error as e:
        print(f"  [DB Error] {e}")
        print(f"  [DB] Falling back to hardcoded keywords")
        return {}


def fetch_trends_for_categories(
    categories: list,
    keywords_map: dict,
    timeframe: str = "today 12-m",
    use_db_keywords: bool = False,
    months_back: int = 3,
) -> pd.DataFrame:
    """
    For each category fetch Google Trends interest for its keywords.
    Scores are 0-100 relative scale (100 = peak search interest).
    Batched in groups of 5 to stay within pytrends limits.

    Args:
        categories: List of category names to fetch trends for
        keywords_map: Fallback mapping of categories to keywords
        timeframe: Google Trends timeframe string
        use_db_keywords: If True, query keywords from database
        months_back: If using DB, how many months to look back
    """
    # Get keywords from DB if requested
    if use_db_keywords:
        db_keywords = get_keywords_from_db(categories, months_back=months_back)
        # Merge DB keywords with fallback (prefer DB keywords)
        for cat in categories:
            if cat in db_keywords and db_keywords[cat]:
                keywords_map[cat] = db_keywords[cat]

    pytrends = TrendReq(hl="en-US", tz=300)
    all_rows  = []

    for cat in categories:
        keywords = keywords_map.get(cat, [])
        if not keywords:
            print(f"[Trends] No keywords for {cat}, skipping...")
            continue

        print(f"[Trends] {cat}: {keywords}")
        batches        = [keywords[i:i+5] for i in range(0, len(keywords), 5)]
        keyword_scores = {}

        for batch in batches:
            try:
                pytrends.build_payload(batch, timeframe=timeframe, geo="US")
                df_interest = pytrends.interest_over_time()
                if df_interest.empty:
                    continue
                for kw in batch:
                    if kw in df_interest.columns:
                        keyword_scores[kw] = round(df_interest[kw].mean(), 1)
            except Exception as e:
                print(f"  [warn] Trends error for batch {batch}: {e}")
            time.sleep(1.5)

        if not keyword_scores:
            continue

        sorted_kws = sorted(keyword_scores.items(), key=lambda x: x[1], reverse=True)
        for rank, (kw, score) in enumerate(sorted_kws, start=1):
            all_rows.append({
                "Category":     cat,
                "Keyword":      kw,
                "Avg Interest": score,
                "Rank in Cat":  rank,
            })

    return pd.DataFrame(all_rows)
