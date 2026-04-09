# WigglNet UI

Web interface for the WigglNet data-powered eCommerce market analytics and predictions platform.

## Features

### Landing Page
- **Spinning Globe Word Cloud**: 3D interactive word cloud visualization of trending keywords
- **Animated Taglines**: 30+ rhyming taglines rotating every 3 seconds
- **Platform Overview**: Scrollable sections explaining WigglNet's capabilities
- **Dark Terminal Aesthetic**: Modern, professional UI with IBM Plex Mono, Syne, and Epilogue fonts

### Database Explorer
- **Tree Navigation**: Left sidebar with all 8 database tables
- **Data Viewer**: Browse table contents with pagination (100 records per page)
- **Schema Inspector**: View table schemas with column types, keys, and constraints
- **Export**: Download table data as CSV
- **Interactive**: Click table names to view data or schema

## Database Tables

1. **ARTICLES** 📄 - Article content from RSS feeds
2. **KEYWORDS** 🔑 - Extracted keywords
3. **ARTICLE_KEYWORDS** 🔗 - Article-keyword relationships
4. **ENTITIES** 🏢 - Named entities (orgs, people, products)
5. **ARTICLE_ENTITY_SENTIMENT** 💭 - Entity sentiment analysis
6. **PRICE_HISTORY** 💰 - Amazon ASIN price tracking
7. **BLS_CPI_DATA** 📊 - Bureau of Labor Statistics CPI data
8. **SPENDING_TRENDS** 📈 - Google Trends spending data

## Installation

1. Install dependencies:
```bash
cd ui
pip install -r requirements.txt
```

2. Ensure the database credentials are configured in `.env` file in the parent directory:
```env
DB_HOST=192.168.1.22
DB_USER=nunya
DB_PASSWORD=your_password
DB_NAME=GWD_WEBDATA
DB_PORT=3306
```

## Running the Server

```bash
python main.py
```

The server will start on `http://localhost:8001`

## Architecture

```
ui/
├── main.py                 # FastAPI backend server
├── requirements.txt        # Python dependencies
├── templates/
│   ├── index.html         # Landing page
│   └── explorer.html      # Database explorer
└── static/
    ├── css/
    │   └── style.css      # Dark terminal styling
    └── js/
        ├── globe.js       # 3D spinning word cloud
        ├── taglines.js    # Tagline rotator
        └── explorer.js    # Database explorer logic
```

## API Endpoints

- `GET /` - Landing page
- `GET /explorer` - Database explorer
- `GET /wordcloud-data` - Keyword data for word cloud (JSON)
- `GET /api/tables` - List all tables (JSON)
- `GET /api/table/{table_name}` - Get table data with pagination
- `GET /api/table/{table_name}/schema` - Get table schema

## Design System

### Colors
- Surface: `#080d12`
- Accent: `#00c8ff` (cyan)
- Success: `#00ff88`
- Text Primary: `#e6e6e6`
- Text Secondary: `#999999`

### Fonts
- Display: Syne (800 weight)
- Body: Epilogue (400, 600)
- Mono: IBM Plex Mono (400, 600)

## Technologies

- **Backend**: FastAPI + Python 3.11
- **Database**: MySQL/MariaDB (via mysql-connector)
- **Frontend**: Vanilla JavaScript (no frameworks)
- **Styling**: Custom CSS with CSS Grid and Flexbox
- **Visualization**: Canvas API for 3D word cloud

## Integration with `/app`

The UI server imports shared utilities from the `/app` directory:
- `app.shared_utils.db_utils` - Database connection utilities

This allows the UI to connect to the same database that the data collection scripts use.

## Development

### Adding New Tables
1. Add table definition to `TABLES` array in `main.py`
2. Include icon emoji and description
3. Table will automatically appear in the explorer sidebar

### Customizing Word Cloud
- Modify `/wordcloud-data` endpoint to change keyword source
- Adjust `radius`, `minSize`, `maxSize` in `globe.js` to change appearance
- Change rotation speed by modifying `this.rotation.y += 0.003` in `animate()`

### Styling
All styles are in `/static/css/style.css`. The design uses CSS custom properties (variables) for easy theming.

## Browser Support

- Chrome/Edge 90+
- Firefox 88+
- Safari 14+

Requires JavaScript enabled for interactive features.

## License

Part of the WigglNet Analytics Platform.
