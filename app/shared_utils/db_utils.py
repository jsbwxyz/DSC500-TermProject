"""
Database utilities for wigglnet-data-engine
Consolidates database connection and configuration logic
"""

import os
from typing import Optional, Dict
import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


def get_db_config() -> Dict[str, any]:
    """
    Load database configuration from environment variables

    Returns:
        dict: Database configuration dictionary

    Raises:
        ValueError: If DB_PASSWORD is not set in environment variables
    """
    password = os.getenv('DB_PASSWORD')
    if not password:
        raise ValueError(
            "DB_PASSWORD not found in environment variables. "
            "Please create a .env file from .env.example and set your credentials."
        )

    return {
        'host': os.getenv('DB_HOST', '192.168.1.22'),
        'user': os.getenv('DB_USER', 'nunya'),
        'password': password,
        'database': os.getenv('DB_NAME', 'GWD_WEBDATA'),
        'port': int(os.getenv('DB_PORT', '3306'))
    }


def connect_database() -> Optional[mysql.connector.connection.MySQLConnection]:
    """
    Connect to the MySQL database using configuration from environment variables

    Returns:
        MySQLConnection object if successful, None otherwise
    """
    try:
        config = get_db_config()
        conn = mysql.connector.connect(**config)
        print("Successfully connected to database")
        return conn
    except Error as err:
        print(f"Error connecting to database: {err}")
        return None


def ensure_connection(conn: mysql.connector.connection.MySQLConnection) -> bool:
    """
    Check if connection is alive and reconnect if necessary

    Args:
        conn: MySQL connection object

    Returns:
        bool: True if connection is alive or successfully reconnected
    """
    try:
        if conn and conn.is_connected():
            return True
        else:
            print("Connection lost, attempting to reconnect...")
            conn = connect_database()
            return conn is not None
    except Error:
        return False
