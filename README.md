# MTB Data Engine

A minimal data collection and database management system for three data sources:

1. **Article Keywords** - Scrapes articles from RSS feeds and HTML pages, extracts keywords
2. **Product Pricing** - Tracks Amazon product prices over time
3. **Discretionary Spending** - Collects BLS CPI data and Google Trends for consumer spending insights

## Directory Structure

```
mtb_data_engine/
├── db_uploader.py              # Orchestrator - delegates to individual uploaders
├── DATABASE_SCHEMA.md          # Complete database schema documentation
├── requirements.txt            # Python dependencies
├── README.md
│
├── keywords/                   # Article keyword extraction
│   ├── data/                   # JSON output files
│   ├── tools/
│   │   ├── keyword_extractor.py
│   │   └── db_uploader.py      # Article upload script
│   ├── rss_scraper.py
│   ├── web_scraper.py
│   ├── run.py                  # Manual scraper
│   └── auto.py                 # Automated 12-hour scraper
│
├── pricing/                    # Amazon price tracking
│   ├── data/                   # JSON output files (all_prices.json)
│   ├── main.py                 # Price scraper
│   ├── timing.py               # Scheduling
│   └── upload_db.py            # Pricing upload script
│
└── spending/                   # Discretionary spending intelligence
    ├── data/                   # CSV output files
    ├── discretionary_pipeline.py
    └── upload_db.py            # Spending upload script
```

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Setup Database

Run the SQL script in `DATABASE_SCHEMA.md` to create all required tables in your MySQL database.

### 3. Configure Database Connection

Edit `db_uploader.py` and update the `DB_CONFIG` dictionary with your database credentials:

```python
DB_CONFIG = {
    'host': 'your_host',
    'user': 'your_user',
    'password': 'your_password',
    'database': 'GWD_WEBDATA',
    'port': 3306
}
```

## Usage

### Database Operations

Database uploads can be done two ways:

**Option 1: Use the root orchestrator** (delegates to individual scripts):
```bash
python db_uploader.py sync              # Check sync for all sources
python db_uploader.py upload-articles   # Upload article keywords
python db_uploader.py upload-prices     # Upload product prices
python db_uploader.py upload-disc       # Upload discretionary spending (interactive)
```

**Option 2: Run individual upload scripts directly**:
```bash
cd keywords/tools && python db_uploader.py
cd pricing && python upload_db.py
cd spending && python upload_db.py
```

### Data Collection

**Collect article keywords**:
```bash
cd keywords
python run.py
```

**Collect product prices**:
```bash
cd pricing
python main.py B08573DQ39  # Single ASIN
python timing.py           # Scheduled collection
```

**Collect discretionary spending data**:
```bash
cd spending
python discretionary_pipeline.py
```

## Data Sources

### Article Keywords
- RSS feeds from design/home magazines
- HTML page scraping
- Keyword extraction using AI/NLP
- Output: `keywords/data/*.json`

### Product Pricing
- Amazon product price tracking via Selenium
- Multiple ASINs monitored
- Price history tracking
- Output: `pricing/data/all_prices.json`

### Discretionary Spending
- BLS CPI data for discretionary categories
- Google Trends for product-level insights
- Demand signal analysis
- Output: `spending/data/*.csv`
  - `discretionary_bls_summary.csv` - Latest month summary by category
  - `discretionary_bls_monthly.csv` - 12 months of historical data
  - `discretionary_trends_summary.csv` - Google Trends product interest

## Architecture

### Modular Design

Each data source has its own upload script that handles:
- Database connection for that source
- Sync checking (comparing local files to database)
- Data insertion with duplicate prevention
- Source-specific data transformations

The root `db_uploader.py` is a lightweight orchestrator that:
- Delegates to individual upload scripts
- Provides unified sync checking across all sources
- Offers convenience commands for common operations

### Sync Feature

The sync feature compares your local JSON/CSV files with the database to identify:
- Missing records that need to be uploaded
- Current sync status for each data source
- Prevents duplicate uploads

Run `python db_uploader.py sync` regularly to ensure your database is up-to-date.

## Requirements

- Python 3.8+
- MySQL database
- Chrome/Chromium (for Selenium scrapers)
- Internet connection for data collection
