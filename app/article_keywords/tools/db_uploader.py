"""
Article Keywords Database Uploader
Uploads articles with keywords to ARTICLES, KEYWORDS, and ARTICLE_KEYWORDS tables
"""

import sys
from pathlib import Path

# Add project root to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

import mysql.connector
from mysql.connector import Error, IntegrityError
import json
from app.shared_utils import get_db_config, get_data_dir

class DatabaseUploader:
    def __init__(self, config=None):
        """Initialize database connection parameters from config dict or environment"""
        if config is None:
            config = get_db_config()

        self.host = config['host']
        self.user = config['user']
        self.password = config['password']
        self.database = config['database']
        self.port = config['port']
        self.connection = None

    def connect(self):
        """Establish connection to the database"""
        try:
            self.connection = mysql.connector.connect(
                host=self.host,
                user=self.user,
                password=self.password,
                database=self.database,
                port=self.port,
                charset='utf8mb4'
            )
            print("Successfully connected to database")
            return True
        except Error as e:
            print(f"Error connecting to database: {e}")
            return False

    def get_or_create_keyword(self, keyword_text: str) -> int:
        """Get existing keyword ID or create new keyword and return its ID"""
        try:
            cursor = self.connection.cursor(dictionary=True)
            cursor.execute("SELECT KEYWORD_ID FROM KEYWORDS WHERE KEYWORD_TEXT = %s", (keyword_text,))
            result = cursor.fetchone()

            if result:
                keyword_id = result['KEYWORD_ID']
                cursor.close()
                return keyword_id

            cursor.execute("INSERT INTO KEYWORDS (KEYWORD_TEXT) VALUES (%s)", (keyword_text,))
            self.connection.commit()
            keyword_id = cursor.lastrowid
            cursor.close()
            return keyword_id
        except Error as e:
            print(f"Error with keyword '{keyword_text}': {e}")
            return None

    def extract_date_only(self, published_date: str) -> str:
        """Extract only the date portion (YYYY-MM-DD) from datetime string"""
        if not published_date:
            return None
        try:
            date_part = published_date.split(' ')[0]
            return date_part
        except Exception as e:
            print(f"Error extracting date from '{published_date}': {e}")
            return None

    def insert_article_with_keywords(self, source_url: str, title: str, description: str,
                                     published_date: str, keywords: list, frequency: int = 1,
                                     entity_sentiment: list = None):
        """Insert article and link it to keywords and entity sentiment"""
        if not self.connection:
            print("No database connection. Call connect() first.")
            return False

        try:
            cursor = self.connection.cursor(dictionary=True)
            cursor.execute("SELECT ARTICLE_ID FROM ARTICLES WHERE SOURCE = %s", (source_url,))
            result = cursor.fetchone()

            date_only = self.extract_date_only(published_date)

            if result:
                article_id = result['ARTICLE_ID']
                print(f"Article already exists (ID: {article_id}): {title[:50]}...")
            else:
                cursor.execute("""
                    INSERT INTO ARTICLES (SOURCE, TITLE, DESCRIPTION, PUBLISHED_DATE)
                    VALUES (%s, %s, %s, %s)
                """, (source_url, title, description, date_only))
                article_id = cursor.lastrowid
                self.connection.commit()

            inserted_count = 0
            for kw_dict in keywords:
                keyword_text = kw_dict.get('keyword', '')
                confidence = kw_dict.get('confidence', 1.0)

                if not keyword_text:
                    continue

                keyword_id = self.get_or_create_keyword(keyword_text)

                if keyword_id:
                    try:
                        cursor.execute("""
                            INSERT INTO ARTICLE_KEYWORDS (ARTICLE_ID, KEYWORD_ID, FREQUENCY, CONFIDENCE)
                            VALUES (%s, %s, %s, %s)
                        """, (article_id, keyword_id, frequency, confidence))
                        inserted_count += 1
                    except IntegrityError:
                        continue

            self.connection.commit()
            cursor.close()
            print(f"Successfully inserted article with {inserted_count} keywords: {title[:50]}...")
            if date_only:
                print(f"  Published: {date_only}")

            # Insert entity sentiment if present
            if entity_sentiment:
                sentiment_count = self.insert_entity_sentiment(article_id, entity_sentiment)
                print(f"  Entity sentiment: {sentiment_count} entities written")

            return True
        except Error as e:
            print(f"Error inserting article: {e}")
            self.connection.rollback()
            return False

    def upload_from_json(self, json_file_path: str):
        """Upload articles from JSON file"""
        try:
            with open(json_file_path, 'r', encoding='utf-8') as f:
                articles = json.load(f)

            print(f"Loaded {len(articles)} articles from {json_file_path}\n")

            total_articles = 0
            total_keywords_linked = 0
            total_skipped = 0

            for article in articles:
                keywords = article.get('keywords', [])

                if not keywords:
                    print(f"Skipping article (no keywords): {article.get('title', 'Unknown')[:50]}...")
                    total_skipped += 1
                    continue

                success = self.insert_article_with_keywords(
                    source_url=article.get('link', ''),
                    title=article.get('title', ''),
                    description=article.get('description', ''),
                    published_date=article.get('published_date'),
                    keywords=keywords,
                    frequency=1,
                    entity_sentiment=article.get('entity_sentiment', [])
                )

                if success:
                    total_articles += 1
                    total_keywords_linked += len(keywords)

            print(f"\n=== Upload Summary ===")
            print(f"Total articles in JSON: {len(articles)}")
            print(f"Articles inserted/updated: {total_articles}")
            print(f"Total keyword links created: {total_keywords_linked}")
            print(f"Articles skipped (no keywords): {total_skipped}")
        except Exception as e:
            print(f"Error processing JSON file: {e}")

    def check_sync(self, data_dir=None):
        """Check if database is synced with JSON files"""
        print("=" * 70)
        print("Checking article keywords sync status...")
        print("=" * 70)

        # Use path_utils if no data_dir provided
        if data_dir is None:
            data_path = get_data_dir('article_keywords')
        else:
            data_path = Path(data_dir)

        file_articles = []

        if not data_path.exists():
            print(f"Data directory not found: {data_path}")
            return {'is_synced': True, 'missing_in_db': []}

        for json_file in data_path.glob("*.json"):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    articles = json.load(f)
                    for article in articles:
                        article['_source_file'] = json_file.name
                        file_articles.append(article)
            except Exception as e:
                print(f"Error reading {json_file.name}: {e}")

        print(f"\nFound {len(file_articles)} articles in JSON files")

        try:
            cursor = self.connection.cursor(dictionary=True)
            cursor.execute("SELECT ARTICLE_ID, SOURCE, TITLE, PUBLISHED_DATE FROM ARTICLES")
            db_articles = cursor.fetchall()
            cursor.close()
        except Error as e:
            print(f"Error fetching articles from database: {e}")
            return {'is_synced': False, 'missing_in_db': []}

        print(f"Found {len(db_articles)} articles in database")

        db_lookup = {}
        for article in db_articles:
            pub_date = str(article.get('PUBLISHED_DATE')) if article.get('PUBLISHED_DATE') else None
            key = (article.get('TITLE', '').strip(), pub_date)
            db_lookup[key] = article

        file_lookup = {}
        for article in file_articles:
            pub_date = self.extract_date_only(article.get('published_date'))
            key = (article.get('title', '').strip(), pub_date)
            if key not in file_lookup:
                file_lookup[key] = article

        missing_in_db = []
        for key, article in file_lookup.items():
            if key not in db_lookup:
                missing_in_db.append(article)

        print("\n" + "=" * 70)
        if len(missing_in_db) == 0:
            print("✓ Article database is UP TO DATE")
        else:
            print(f"⚠ {len(missing_in_db)} article(s) need to be uploaded")
            for i, article in enumerate(missing_in_db[:5], 1):
                title = article.get('title', 'No title')[:60]
                print(f"  {i}. {title}")
            if len(missing_in_db) > 5:
                print(f"  ... and {len(missing_in_db) - 5} more")
        print("=" * 70)

        return {'is_synced': len(missing_in_db) == 0, 'missing_in_db': missing_in_db}

    def insert_entity_sentiment(self, article_id: int, entity_sentiment: list):
        """
        Insert entity sentiment results for an article.

        Writes to ENTITIES and ARTICLE_ENTITY_SENTIMENT tables.
        Skips duplicates silently (same article/entity pair).

        Args:
            article_id (int): ID of the parent article in ARTICLES table.
            entity_sentiment (list): Output from sentiment_analyzer.py —
                list of dicts with keys: entity, entity_type, sentiment,
                confidence, mentions.

        Returns:
            int: Number of entity sentiment rows inserted.
        """
        if not self.connection or not entity_sentiment:
            return 0

        inserted = 0
        cursor = self.connection.cursor(dictionary=True)

        for entry in entity_sentiment:
            entity_text = entry.get('entity', '').strip()
            if not entity_text:
                continue

            # Get or create entity in ENTITIES table
            cursor.execute(
                "SELECT ENTITY_ID FROM ENTITIES WHERE ENTITY_TEXT = %s",
                (entity_text,)
            )
            result = cursor.fetchone()

            if result:
                entity_id = result['ENTITY_ID']
            else:
                cursor.execute(
                    "INSERT INTO ENTITIES (ENTITY_TEXT, ENTITY_TYPE) VALUES (%s, %s)",
                    (entity_text, entry.get('entity_type', 'UNKNOWN'))
                )
                entity_id = cursor.lastrowid

            try:
                cursor.execute("""
                    INSERT INTO ARTICLE_ENTITY_SENTIMENT
                        (ARTICLE_ID, ENTITY_ID, SENTIMENT, CONFIDENCE, MENTIONS)
                    VALUES (%s, %s, %s, %s, %s)
                """, (
                    article_id,
                    entity_id,
                    entry.get('sentiment', 'neutral'),
                    entry.get('confidence', 0.0),
                    entry.get('mentions', 1)
                ))
                inserted += 1
            except IntegrityError:
                continue

        self.connection.commit()
        cursor.close()
        return inserted

    def insert_entity_sentiment(self, article_id: int, entity_sentiment: list):
        """
        Insert entity sentiment results for an article.

        Writes to ENTITIES and ARTICLE_ENTITY_SENTIMENT tables.
        Skips duplicates silently (same article/entity pair).

        Args:
            article_id (int): ID of the parent article in ARTICLES table.
            entity_sentiment (list): Output from sentiment_analyzer.py —
                list of dicts with keys: entity, entity_type, sentiment,
                confidence, mentions.

        Returns:
            int: Number of entity sentiment rows inserted.
        """
        if not self.connection or not entity_sentiment:
            return 0

        inserted = 0
        cursor = self.connection.cursor(dictionary=True)

        for entry in entity_sentiment:
            entity_text = entry.get('entity', '').strip()
            if not entity_text:
                continue

            # Get or create entity in ENTITIES table
            cursor.execute(
                "SELECT ENTITY_ID FROM ENTITIES WHERE ENTITY_TEXT = %s",
                (entity_text,)
            )
            result = cursor.fetchone()

            if result:
                entity_id = result['ENTITY_ID']
            else:
                cursor.execute(
                    "INSERT INTO ENTITIES (ENTITY_TEXT, ENTITY_TYPE) VALUES (%s, %s)",
                    (entity_text, entry.get('entity_type', 'UNKNOWN'))
                )
                entity_id = cursor.lastrowid

            try:
                cursor.execute("""
                    INSERT INTO ARTICLE_ENTITY_SENTIMENT
                        (ARTICLE_ID, ENTITY_ID, SENTIMENT, CONFIDENCE, MENTIONS)
                    VALUES (%s, %s, %s, %s, %s)
                """, (
                    article_id,
                    entity_id,
                    entry.get('sentiment', 'neutral'),
                    entry.get('confidence', 0.0),
                    entry.get('mentions', 1)
                ))
                inserted += 1
            except IntegrityError:
                continue

        self.connection.commit()
        cursor.close()
        return inserted

    def close(self):
        """Close the database connection"""
        if self.connection:
            self.connection.close()
            print("\nDatabase connection closed")


def main():
    """Main upload process"""
    uploader = DatabaseUploader()

    if uploader.connect():
        # Check sync (uses path_utils to get data directory)
        sync_status = uploader.check_sync()

        if not sync_status['is_synced']:
            proceed = input(f"\nUpload {len(sync_status['missing_in_db'])} missing articles? (y/n): ").strip().lower()
            if proceed == 'y':
                data_path = get_data_dir('article_keywords')
                for json_file in data_path.glob("*.json"):
                    print(f"\nProcessing: {json_file.name}")
                    uploader.upload_from_json(str(json_file))

        uploader.close()


if __name__ == "__main__":
    main()
