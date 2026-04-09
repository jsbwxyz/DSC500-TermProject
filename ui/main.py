"""
WigglNet UI Server
FastAPI backend for data-powered eCommerce market analytics platform
"""
import os
import sys
from datetime import datetime
from typing import List, Dict, Any
import json
import io
import base64

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import mysql.connector
from wordcloud import WordCloud
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.patches import Rectangle
import numpy as np

# Add parent directory to path to import shared_utils
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from app.shared_utils.db_utils import get_db_config, connect_database

app = FastAPI(title="WigglNet Analytics UI")

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Templates
templates = Jinja2Templates(directory="templates")

# Database tables
TABLES = [
    {"name": "ARTICLES", "icon": "📄", "description": "Article content from RSS feeds"},
    {"name": "KEYWORDS", "icon": "🔑", "description": "Extracted keywords"},
    {"name": "ARTICLE_KEYWORDS", "icon": "🔗", "description": "Article-keyword relationships"},
    {"name": "ENTITIES", "icon": "🏢", "description": "Named entities (orgs, people, products)"},
    {"name": "ARTICLE_ENTITY_SENTIMENT", "icon": "💭", "description": "Entity sentiment analysis"},
    {"name": "PRICE_HISTORY", "icon": "💰", "description": "Amazon ASIN price tracking"},
    {"name": "BLS_CPI_DATA", "icon": "📊", "description": "Bureau of Labor Statistics CPI data"},
    {"name": "SPENDING_TRENDS", "icon": "📈", "description": "Google Trends spending data"}
]

def get_db_connection():
    """Get database connection using shared utils"""
    try:
        return connect_database()
    except Exception as e:
        print(f"Database connection error: {e}")
        return None

def generate_sentiment_wordcloud(words_data):
    """Generate sentiment word cloud using matplotlib"""
    if not words_data:
        # Return empty image
        fig, ax = plt.subplots(figsize=(10, 6), facecolor='#fafaf8')
        ax.text(0.5, 0.5, 'No sentiment data available',
                ha='center', va='center', fontsize=16, color='#999')
        ax.axis('off')
    else:
        # Create word frequency dict
        word_freq = {}
        for item in words_data:
            text = item.get('text', '')
            weight = item.get('weight', 1)
            word_freq[text] = weight

        # Generate word cloud
        wc = WordCloud(
            width=800,
            height=500,
            background_color='#fafaf8',
            colormap='RdYlGn',
            relative_scaling=0.5,
            min_font_size=10
        ).generate_from_frequencies(word_freq)

        fig, ax = plt.subplots(figsize=(10, 6), facecolor='#fafaf8')
        ax.imshow(wc, interpolation='bilinear')
        ax.axis('off')

    # Save to bytes
    buf = io.BytesIO()
    plt.tight_layout(pad=0)
    plt.savefig(buf, format='png', dpi=100, facecolor='#fafaf8')
    plt.close(fig)
    buf.seek(0)
    return buf

def generate_price_chart(price_data, animated=True):
    """Generate animated price trend chart"""
    fig, ax = plt.subplots(figsize=(10, 5), facecolor='#ffffff')

    if not price_data:
        ax.text(0.5, 0.5, 'No price data available',
                ha='center', va='center', fontsize=16, color='#999',
                transform=ax.transAxes)
        ax.axis('off')
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=100, facecolor='#ffffff')
        plt.close(fig)
        buf.seek(0)
        return buf

    # Extract data
    dates = [item.get('date', i) for i, item in enumerate(price_data)]
    prices = [float(item.get('price', 0)) for item in price_data]

    if animated:
        # Create animated line chart
        line, = ax.plot([], [], linewidth=3, color='#1a1a1a', marker='o', markersize=5)

        ax.set_xlim(0, len(dates)-1)
        ax.set_ylim(min(prices) * 0.95, max(prices) * 1.05)
        ax.set_xlabel('Date', fontsize=12, color='#666')
        ax.set_ylabel('Price ($)', fontsize=12, color='#666')
        ax.set_title('Price Trend Over Time', fontsize=14, fontweight='bold', color='#1a1a1a')
        ax.grid(True, alpha=0.3, linestyle='--')
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)

        def init():
            line.set_data([], [])
            return line,

        def animate_frame(frame):
            x = list(range(frame + 1))
            y = prices[:frame + 1]
            line.set_data(x, y)
            return line,

        anim = animation.FuncAnimation(
            fig, animate_frame, init_func=init,
            frames=len(prices), interval=100, blit=True, repeat=True
        )

        buf = io.BytesIO()
        anim.save(buf, writer='pillow', fps=10, format='gif')
        plt.close(fig)
        buf.seek(0)
        return buf
    else:
        # Static chart
        ax.plot(range(len(prices)), prices, linewidth=3, color='#1a1a1a',
                marker='o', markersize=5)
        ax.set_xlabel('Date', fontsize=12, color='#666')
        ax.set_ylabel('Price ($)', fontsize=12, color='#666')
        ax.set_title('Price Trend Over Time', fontsize=14, fontweight='bold', color='#1a1a1a')
        ax.grid(True, alpha=0.3, linestyle='--')
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)

        buf = io.BytesIO()
        plt.tight_layout()
        plt.savefig(buf, format='png', dpi=100, facecolor='#ffffff')
        plt.close(fig)
        buf.seek(0)
        return buf

def generate_cpi_chart(cpi_data, animated=True):
    """Generate animated CPI bar chart"""
    fig, ax = plt.subplots(figsize=(8, 5), facecolor='#ffffff')

    if not cpi_data:
        ax.text(0.5, 0.5, 'No CPI data available',
                ha='center', va='center', fontsize=16, color='#999',
                transform=ax.transAxes)
        ax.axis('off')
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=100, facecolor='#ffffff')
        plt.close(fig)
        buf.seek(0)
        return buf

    labels = [item.get('label', f'Cat {i}')[:15] for i, item in enumerate(cpi_data)]
    values = [float(item.get('value', 0)) for item in cpi_data]

    if animated:
        bars = ax.bar(range(len(labels)), [0] * len(labels), color='#1a1a1a', alpha=0.8)

        ax.set_ylim(0, max(values) * 1.1)
        ax.set_xticks(range(len(labels)))
        ax.set_xticklabels(labels, rotation=45, ha='right', fontsize=9)
        ax.set_ylabel('YoY % Change', fontsize=11, color='#666')
        ax.set_title('CPI Data by Category', fontsize=13, fontweight='bold', color='#1a1a1a')
        ax.grid(True, axis='y', alpha=0.3, linestyle='--')
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)

        def animate_frame(frame):
            for bar, target_height in zip(bars, values):
                current_height = bar.get_height()
                new_height = min(current_height + target_height / 20, target_height)
                bar.set_height(new_height)
            return bars

        anim = animation.FuncAnimation(
            fig, animate_frame, frames=25, interval=50, blit=True, repeat=True
        )

        buf = io.BytesIO()
        anim.save(buf, writer='pillow', fps=20, format='gif')
        plt.close(fig)
        buf.seek(0)
        return buf
    else:
        ax.bar(range(len(labels)), values, color='#1a1a1a', alpha=0.8)
        ax.set_xticks(range(len(labels)))
        ax.set_xticklabels(labels, rotation=45, ha='right', fontsize=9)
        ax.set_ylabel('YoY % Change', fontsize=11, color='#666')
        ax.set_title('CPI Data by Category', fontsize=13, fontweight='bold', color='#1a1a1a')
        ax.grid(True, axis='y', alpha=0.3, linestyle='--')
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)

        buf = io.BytesIO()
        plt.tight_layout()
        plt.savefig(buf, format='png', dpi=100, facecolor='#ffffff')
        plt.close(fig)
        buf.seek(0)
        return buf

def generate_trends_chart(trends_data, animated=True):
    """Generate animated spending trends bar chart"""
    fig, ax = plt.subplots(figsize=(8, 5), facecolor='#ffffff')

    if not trends_data:
        ax.text(0.5, 0.5, 'No trends data available',
                ha='center', va='center', fontsize=16, color='#999',
                transform=ax.transAxes)
        ax.axis('off')
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=100, facecolor='#ffffff')
        plt.close(fig)
        buf.seek(0)
        return buf

    keywords = [item.get('keyword', f'KW{i}')[:12] for i, item in enumerate(trends_data)]
    interests = [float(item.get('interest', 0)) for item in trends_data]

    if animated:
        bars = ax.bar(range(len(keywords)), [0] * len(keywords), color='#0066ff', alpha=0.8)

        ax.set_ylim(0, max(interests) * 1.1)
        ax.set_xticks(range(len(keywords)))
        ax.set_xticklabels(keywords, rotation=45, ha='right', fontsize=9)
        ax.set_ylabel('Interest Score', fontsize=11, color='#666')
        ax.set_title('Spending Trends', fontsize=13, fontweight='bold', color='#1a1a1a')
        ax.grid(True, axis='y', alpha=0.3, linestyle='--')
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)

        def animate_frame(frame):
            for bar, target_height in zip(bars, interests):
                current_height = bar.get_height()
                new_height = min(current_height + target_height / 20, target_height)
                bar.set_height(new_height)
            return bars

        anim = animation.FuncAnimation(
            fig, animate_frame, frames=25, interval=50, blit=True, repeat=True
        )

        buf = io.BytesIO()
        anim.save(buf, writer='pillow', fps=20, format='gif')
        plt.close(fig)
        buf.seek(0)
        return buf
    else:
        ax.bar(range(len(keywords)), interests, color='#0066ff', alpha=0.8)
        ax.set_xticks(range(len(keywords)))
        ax.set_xticklabels(keywords, rotation=45, ha='right', fontsize=9)
        ax.set_ylabel('Interest Score', fontsize=11, color='#666')
        ax.set_title('Spending Trends', fontsize=13, fontweight='bold', color='#1a1a1a')
        ax.grid(True, axis='y', alpha=0.3, linestyle='--')
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)

        buf = io.BytesIO()
        plt.tight_layout()
        plt.savefig(buf, format='png', dpi=100, facecolor='#ffffff')
        plt.close(fig)
        buf.seek(0)
        return buf

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Landing page with spinning globe word cloud"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/wordcloud-data")
async def wordcloud_data():
    """Get keyword data for word cloud"""
    conn = get_db_connection()
    if not conn:
        # Return sample data if DB unavailable
        return JSONResponse({
            "keywords": [
                {"text": "analytics", "weight": 100},
                {"text": "ecommerce", "weight": 90},
                {"text": "machine learning", "weight": 85},
                {"text": "predictions", "weight": 80},
                {"text": "market", "weight": 75},
                {"text": "data", "weight": 70},
                {"text": "trends", "weight": 65},
                {"text": "insights", "weight": 60}
            ]
        })

    try:
        cursor = conn.cursor(dictionary=True)
        query = """
        SELECT k.KEYWORD_TEXT,
               COUNT(DISTINCT ak.ARTICLE_ID) AS article_count,
               SUM(ak.FREQUENCY) AS total_frequency
        FROM ARTICLE_KEYWORDS ak
        JOIN KEYWORDS k ON k.KEYWORD_ID = ak.KEYWORD_ID
        JOIN ARTICLES a ON a.ARTICLE_ID = ak.ARTICLE_ID
        WHERE a.PUBLISHED_DATE >= DATE_SUB(NOW(), INTERVAL 6 MONTH)
        GROUP BY k.KEYWORD_ID, k.KEYWORD_TEXT
        ORDER BY article_count DESC, total_frequency DESC
        LIMIT 100
        """
        cursor.execute(query)
        results = cursor.fetchall()

        keywords = [
            {
                "text": row["KEYWORD_TEXT"],
                "weight": int(row["total_frequency"])
            }
            for row in results
        ]

        cursor.close()
        conn.close()

        return JSONResponse({"keywords": keywords})
    except Exception as e:
        print(f"Error fetching keyword data: {e}")
        return JSONResponse({"keywords": []})

@app.get("/explorer", response_class=HTMLResponse)
async def explorer(request: Request):
    """Database explorer page"""
    return templates.TemplateResponse("explorer.html", {
        "request": request,
        "tables": TABLES
    })

@app.get("/api/tables")
async def list_tables():
    """Get list of all tables"""
    return JSONResponse({"tables": TABLES})

@app.get("/api/table/{table_name}")
async def get_table_data(table_name: str, limit: int = 100, offset: int = 0):
    """Get data from a specific table"""
    # Validate table name
    valid_tables = [t["name"] for t in TABLES]
    if table_name not in valid_tables:
        raise HTTPException(status_code=404, detail="Table not found")

    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")

    try:
        cursor = conn.cursor(dictionary=True)

        # Get total count
        count_query = f"SELECT COUNT(*) as total FROM {table_name}"
        cursor.execute(count_query)
        total = cursor.fetchone()["total"]

        # Get data
        query = f"SELECT * FROM {table_name} LIMIT {limit} OFFSET {offset}"
        cursor.execute(query)
        rows = cursor.fetchall()

        # Get column names
        columns = [desc[0] for desc in cursor.description] if cursor.description else []

        cursor.close()
        conn.close()

        return JSONResponse({
            "table": table_name,
            "columns": columns,
            "rows": rows,
            "total": total,
            "limit": limit,
            "offset": offset
        })
    except Exception as e:
        print(f"Error fetching table data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/table/{table_name}/schema")
async def get_table_schema(table_name: str):
    """Get schema information for a table"""
    valid_tables = [t["name"] for t in TABLES]
    if table_name not in valid_tables:
        raise HTTPException(status_code=404, detail="Table not found")

    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")

    try:
        cursor = conn.cursor(dictionary=True)
        query = f"DESCRIBE {table_name}"
        cursor.execute(query)
        schema = cursor.fetchall()

        cursor.close()
        conn.close()

        return JSONResponse({"table": table_name, "schema": schema})
    except Exception as e:
        print(f"Error fetching schema: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/chart/sentiment/{search_term}")
async def get_sentiment_chart(search_term: str):
    """Generate sentiment word cloud chart"""
    conn = get_db_connection()
    words_data = []

    if conn:
        try:
            cursor = conn.cursor(dictionary=True)
            query = """
            SELECT
                e.ENTITY_TEXT as text,
                SUM(aes.MENTIONS) as weight
            FROM ARTICLE_ENTITY_SENTIMENT aes
            JOIN ENTITIES e ON e.ENTITY_ID = aes.ENTITY_ID
            JOIN ARTICLES a ON a.ARTICLE_ID = aes.ARTICLE_ID
            JOIN ARTICLE_KEYWORDS ak ON ak.ARTICLE_ID = a.ARTICLE_ID
            JOIN KEYWORDS k ON k.KEYWORD_ID = ak.KEYWORD_ID
            WHERE k.KEYWORD_TEXT LIKE %s
            GROUP BY e.ENTITY_TEXT
            ORDER BY weight DESC
            LIMIT 50
            """
            cursor.execute(query, (f'%{search_term}%',))
            words_data = cursor.fetchall()
            cursor.close()
            conn.close()
        except Exception as e:
            print(f"Error fetching sentiment data: {e}")

    img_buffer = generate_sentiment_wordcloud(words_data)
    return StreamingResponse(img_buffer, media_type="image/png")

@app.get("/api/chart/price/{search_term}")
async def get_price_chart(search_term: str, animated: bool = True):
    """Generate price trend chart"""
    conn = get_db_connection()
    price_data = []

    if conn:
        try:
            cursor = conn.cursor(dictionary=True)
            query = """
            SELECT
                DATE(TIMESTAMP) as date,
                AVG(PRICE) as price
            FROM PRICE_HISTORY
            WHERE ASIN IN (
                SELECT DISTINCT ASIN
                FROM PRICE_HISTORY
                LIMIT 1
            )
            GROUP BY DATE(TIMESTAMP)
            ORDER BY DATE(TIMESTAMP) ASC
            LIMIT 30
            """
            cursor.execute(query)
            price_data = cursor.fetchall()
            cursor.close()
            conn.close()
        except Exception as e:
            print(f"Error fetching price data: {e}")

    img_buffer = generate_price_chart(price_data, animated=animated)
    media_type = "image/gif" if animated else "image/png"
    return StreamingResponse(img_buffer, media_type=media_type)

@app.get("/api/chart/cpi/{search_term}")
async def get_cpi_chart(search_term: str, animated: bool = True):
    """Generate CPI bar chart"""
    conn = get_db_connection()
    cpi_data = []

    if conn:
        try:
            cursor = conn.cursor(dictionary=True)
            query = """
            SELECT
                CATEGORY as label,
                AVG(YOY_PCT) as value
            FROM BLS_CPI_DATA
            GROUP BY CATEGORY
            LIMIT 8
            """
            cursor.execute(query)
            cpi_data = cursor.fetchall()
            cursor.close()
            conn.close()
        except Exception as e:
            print(f"Error fetching CPI data: {e}")

    img_buffer = generate_cpi_chart(cpi_data, animated=animated)
    media_type = "image/gif" if animated else "image/png"
    return StreamingResponse(img_buffer, media_type=media_type)

@app.get("/api/chart/trends/{search_term}")
async def get_trends_chart(search_term: str, animated: bool = True):
    """Generate spending trends chart"""
    conn = get_db_connection()
    trends_data = []

    if conn:
        try:
            cursor = conn.cursor(dictionary=True)
            query = """
            SELECT
                KEYWORD as keyword,
                AVG_INTEREST as interest
            FROM SPENDING_TRENDS
            ORDER BY AVG_INTEREST DESC
            LIMIT 10
            """
            cursor.execute(query)
            trends_data = cursor.fetchall()
            cursor.close()
            conn.close()
        except Exception as e:
            print(f"Error fetching trends data: {e}")

    img_buffer = generate_trends_chart(trends_data, animated=animated)
    media_type = "image/gif" if animated else "image/png"
    return StreamingResponse(img_buffer, media_type=media_type)

@app.get("/api/search")
async def search(q: str):
    """Search for keyword/category and return analysis results"""
    conn = get_db_connection()

    # Default/fallback data
    result = {
        "searchTerm": q,
        "sentimentWords": [],
        "priceHistory": [],
        "cpiData": [],
        "trendsData": [],
        "tableData": []
    }

    if not conn:
        return JSONResponse(result)

    try:
        cursor = conn.cursor(dictionary=True)

        # Get sentiment words related to keyword
        sentiment_query = """
        SELECT
            e.ENTITY_TEXT as text,
            aes.SENTIMENT as sentiment,
            SUM(aes.MENTIONS) as weight
        FROM ARTICLE_ENTITY_SENTIMENT aes
        JOIN ENTITIES e ON e.ENTITY_ID = aes.ENTITY_ID
        JOIN ARTICLES a ON a.ARTICLE_ID = aes.ARTICLE_ID
        JOIN ARTICLE_KEYWORDS ak ON ak.ARTICLE_ID = a.ARTICLE_ID
        JOIN KEYWORDS k ON k.KEYWORD_ID = ak.KEYWORD_ID
        WHERE k.KEYWORD_TEXT LIKE %s
        GROUP BY e.ENTITY_TEXT, aes.SENTIMENT
        ORDER BY weight DESC
        LIMIT 20
        """
        cursor.execute(sentiment_query, (f'%{q}%',))
        sentiment_results = cursor.fetchall()
        result["sentimentWords"] = sentiment_results

        # Get price history (if any matching ASIN)
        price_query = """
        SELECT
            DATE(TIMESTAMP) as date,
            AVG(PRICE) as price
        FROM PRICE_HISTORY
        WHERE ASIN IN (
            SELECT DISTINCT ASIN
            FROM PRICE_HISTORY
            LIMIT 1
        )
        GROUP BY DATE(TIMESTAMP)
        ORDER BY DATE(TIMESTAMP) DESC
        LIMIT 30
        """
        cursor.execute(price_query)
        price_results = cursor.fetchall()
        result["priceHistory"] = price_results

        # Get CPI data
        cpi_query = """
        SELECT
            CATEGORY as label,
            AVG(YOY_PCT) as value
        FROM BLS_CPI_DATA
        GROUP BY CATEGORY
        LIMIT 8
        """
        cursor.execute(cpi_query)
        cpi_results = cursor.fetchall()
        result["cpiData"] = cpi_results

        # Get trends data
        trends_query = """
        SELECT
            KEYWORD as keyword,
            AVG_INTEREST as interest
        FROM SPENDING_TRENDS
        ORDER BY AVG_INTEREST DESC
        LIMIT 10
        """
        cursor.execute(trends_query)
        trends_results = cursor.fetchall()
        result["trendsData"] = trends_results

        # Get detailed table data
        table_query = """
        SELECT
            COUNT(DISTINCT a.ARTICLE_ID) as val,
            k.KEYWORD_TEXT as keyword,
            'N/A' as product,
            COALESCE(aes.SENTIMENT, 'neutral') as sentiment,
            AVG(COALESCE(aes.CONFIDENCE, 0.5)) as confidence
        FROM KEYWORDS k
        LEFT JOIN ARTICLE_KEYWORDS ak ON ak.KEYWORD_ID = k.KEYWORD_ID
        LEFT JOIN ARTICLES a ON a.ARTICLE_ID = ak.ARTICLE_ID
        LEFT JOIN ARTICLE_ENTITY_SENTIMENT aes ON aes.ARTICLE_ID = a.ARTICLE_ID
        WHERE k.KEYWORD_TEXT LIKE %s
        GROUP BY k.KEYWORD_TEXT, aes.SENTIMENT
        LIMIT 50
        """
        cursor.execute(table_query, (f'%{q}%',))
        table_results = cursor.fetchall()
        result["tableData"] = table_results

        cursor.close()
        conn.close()

        return JSONResponse(result)

    except Exception as e:
        print(f"Error in search: {e}")
        return JSONResponse(result)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
