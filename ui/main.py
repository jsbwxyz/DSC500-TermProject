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
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import mysql.connector
from wordcloud import WordCloud
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
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
