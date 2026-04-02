# Database Schema for MTB Data Engine

This document describes the MySQL database schema for all three data sources.

## Database Configuration

```
Host: 192.168.1.22 (NAS)
Database: GWD_WEBDATA
Port: 3306
```

## Table Schemas

### 1. Article Keywords Tables

#### ARTICLES Table
Stores scraped articles from RSS feeds and HTML sources.

```sql
CREATE TABLE ARTICLES (
    ARTICLE_ID INT AUTO_INCREMENT PRIMARY KEY,
    SOURCE VARCHAR(500) NOT NULL UNIQUE,
    TITLE VARCHAR(500),
    DESCRIPTION TEXT,
    PUBLISHED_DATE DATE,
    CREATED_AT TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_published_date (PUBLISHED_DATE),
    INDEX idx_source (SOURCE(255))
);
```

#### KEYWORDS Table
Stores unique keywords extracted from articles.

```sql
CREATE TABLE KEYWORDS (
    KEYWORD_ID INT AUTO_INCREMENT PRIMARY KEY,
    KEYWORD_TEXT VARCHAR(255) NOT NULL UNIQUE,
    CREATED_AT TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_keyword_text (KEYWORD_TEXT)
);
```

#### ARTICLE_KEYWORDS Table
Junction table linking articles to keywords with confidence scores.

```sql
CREATE TABLE ARTICLE_KEYWORDS (
    ARTICLE_ID INT NOT NULL,
    KEYWORD_ID INT NOT NULL,
    FREQUENCY INT DEFAULT 1,
    CONFIDENCE DECIMAL(5,4) DEFAULT 1.0000,
    CREATED_AT TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (ARTICLE_ID, KEYWORD_ID),
    FOREIGN KEY (ARTICLE_ID) REFERENCES ARTICLES(ARTICLE_ID) ON DELETE CASCADE,
    FOREIGN KEY (KEYWORD_ID) REFERENCES KEYWORDS(KEYWORD_ID) ON DELETE CASCADE
);
```

### 2. Product Pricing Table

#### PRICE_HISTORY Table
Stores Amazon product price history.

```sql
CREATE TABLE PRICE_HISTORY (
    ID INT AUTO_INCREMENT PRIMARY KEY,
    ASIN VARCHAR(20) NOT NULL,
    PRICE FLOAT NOT NULL,
    RAW_PRICE VARCHAR(50),
    TIMESTAMP DATETIME NOT NULL,
    CREATED_AT TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_asin (ASIN),
    INDEX idx_timestamp (TIMESTAMP),
    UNIQUE KEY unique_price_entry (ASIN, TIMESTAMP)
);
```

**Column Descriptions:**
- `ASIN`: Amazon Standard Identification Number
- `PRICE`: Numeric price value (e.g., 49.99)
- `RAW_PRICE`: Original price string from Amazon (e.g., "$49.99")
- `TIMESTAMP`: When the price was recorded

### 3. Discretionary Spending Tables

#### BLS_CPI Table
Stores Bureau of Labor Statistics Consumer Price Index data.

```sql
CREATE TABLE BLS_CPI (
    ID INT AUTO_INCREMENT PRIMARY KEY,
    CATEGORY VARCHAR(100) NOT NULL,
    DATE VARCHAR(10) NOT NULL,
    CPI_VALUE FLOAT,
    MOM_PCT FLOAT,
    YOY_PCT FLOAT,
    DEMAND_SIGNAL VARCHAR(20),
    CREATED_AT TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_category (CATEGORY),
    INDEX idx_date (DATE),
    UNIQUE KEY unique_bls_entry (CATEGORY, DATE)
);
```

**Column Descriptions:**
- `CATEGORY`: CPI category (e.g., "Recreation", "Food Away From Home")
- `DATE`: Month in YYYY-MM format
- `CPI_VALUE`: Raw CPI index value
- `MOM_PCT`: Month-over-month percentage change
- `YOY_PCT`: Year-over-year percentage change
- `DEMAND_SIGNAL`: "Strong", "Moderate", or "Soft"

#### TRENDS_DATA Table
Stores Google Trends search interest data.

```sql
CREATE TABLE TRENDS_DATA (
    ID INT AUTO_INCREMENT PRIMARY KEY,
    CATEGORY VARCHAR(100) NOT NULL,
    KEYWORD VARCHAR(100) NOT NULL,
    AVG_INTEREST FLOAT,
    RANK_IN_CAT INT,
    LAST_UPDATED TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_category (CATEGORY),
    INDEX idx_keyword (KEYWORD),
    UNIQUE KEY unique_trends_entry (CATEGORY, KEYWORD)
);
```

**Column Descriptions:**
- `CATEGORY`: BLS category the keyword belongs to
- `KEYWORD`: Search term (e.g., "pickleball paddle")
- `AVG_INTEREST`: Average Google Trends interest score (0-100)
- `RANK_IN_CAT`: Rank within the category by interest
- `LAST_UPDATED`: Automatically updated when record changes

## Quick Setup Script

Run this SQL script to create all tables:

```sql
-- Create all tables for MTB Data Engine

-- Article Keywords Tables
CREATE TABLE ARTICLES (
    ARTICLE_ID INT AUTO_INCREMENT PRIMARY KEY,
    SOURCE VARCHAR(500) NOT NULL UNIQUE,
    TITLE VARCHAR(500),
    DESCRIPTION TEXT,
    PUBLISHED_DATE DATE,
    CREATED_AT TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_published_date (PUBLISHED_DATE),
    INDEX idx_source (SOURCE(255))
);

CREATE TABLE KEYWORDS (
    KEYWORD_ID INT AUTO_INCREMENT PRIMARY KEY,
    KEYWORD_TEXT VARCHAR(255) NOT NULL UNIQUE,
    CREATED_AT TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_keyword_text (KEYWORD_TEXT)
);

CREATE TABLE ARTICLE_KEYWORDS (
    ARTICLE_ID INT NOT NULL,
    KEYWORD_ID INT NOT NULL,
    FREQUENCY INT DEFAULT 1,
    CONFIDENCE DECIMAL(5,4) DEFAULT 1.0000,
    CREATED_AT TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (ARTICLE_ID, KEYWORD_ID),
    FOREIGN KEY (ARTICLE_ID) REFERENCES ARTICLES(ARTICLE_ID) ON DELETE CASCADE,
    FOREIGN KEY (KEYWORD_ID) REFERENCES KEYWORDS(KEYWORD_ID) ON DELETE CASCADE
);

-- Product Pricing Table
CREATE TABLE PRICE_HISTORY (
    ID INT AUTO_INCREMENT PRIMARY KEY,
    ASIN VARCHAR(20) NOT NULL,
    PRICE FLOAT NOT NULL,
    RAW_PRICE VARCHAR(50),
    TIMESTAMP DATETIME NOT NULL,
    CREATED_AT TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_asin (ASIN),
    INDEX idx_timestamp (TIMESTAMP),
    UNIQUE KEY unique_price_entry (ASIN, TIMESTAMP)
);

-- Discretionary Spending Tables
CREATE TABLE BLS_CPI (
    ID INT AUTO_INCREMENT PRIMARY KEY,
    CATEGORY VARCHAR(100) NOT NULL,
    DATE VARCHAR(10) NOT NULL,
    CPI_VALUE FLOAT,
    MOM_PCT FLOAT,
    YOY_PCT FLOAT,
    DEMAND_SIGNAL VARCHAR(20),
    CREATED_AT TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_category (CATEGORY),
    INDEX idx_date (DATE),
    UNIQUE KEY unique_bls_entry (CATEGORY, DATE)
);

CREATE TABLE TRENDS_DATA (
    ID INT AUTO_INCREMENT PRIMARY KEY,
    CATEGORY VARCHAR(100) NOT NULL,
    KEYWORD VARCHAR(100) NOT NULL,
    AVG_INTEREST FLOAT,
    RANK_IN_CAT INT,
    LAST_UPDATED TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_category (CATEGORY),
    INDEX idx_keyword (KEYWORD),
    UNIQUE KEY unique_trends_entry (CATEGORY, KEYWORD)
);
```

## Usage Examples

### Check Sync Status
```bash
python db_uploader.py sync
```

### Upload Article Keywords
```bash
python db_uploader.py upload-articles
```

### Upload Product Prices
```bash
python db_uploader.py upload-prices
```

### Upload BLS CPI Summary Data
```bash
python db_uploader.py upload-bls
```

### Upload BLS CPI Monthly Data
```bash
python db_uploader.py upload-bls-monthly
```

### Upload Google Trends Data
```bash
python db_uploader.py upload-trends
```

## Data Flow

1. **Article Keywords**: JSON files in `article_keywords/data/` → ARTICLES, KEYWORDS, ARTICLE_KEYWORDS tables
2. **Product Pricing**: JSON file at `product_pricing/data/all_prices.json` → PRICE_HISTORY table
3. **Discretionary Spending**: CSV files in `disc_spending/data/` → BLS_CPI and TRENDS_DATA tables
   - `discretionary_bls_summary.csv` - Latest month summary (8 categories)
   - `discretionary_bls_monthly.csv` - 12 months historical (96 rows)
   - `discretionary_trends_summary.csv` - Google Trends product keywords

## Notes

- All tables use `TIMESTAMP` fields for tracking when records were created/updated
- Duplicate prevention is handled via `UNIQUE` constraints and sync checking
- Foreign key constraints ensure referential integrity for article-keyword relationships
- Indexes are added on frequently queried columns for performance
