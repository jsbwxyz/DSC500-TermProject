"""
Date utilities for wigglnet-data-engine
Consolidates date parsing and formatting functions
"""

from typing import Optional
from dateutil import parser as date_parser


def parse_publish_date(date_string: str) -> Optional[str]:
    """
    Parse various date formats and return MySQL-compatible datetime string

    Args:
        date_string: Date string in various formats

    Returns:
        str: MySQL-compatible datetime string (YYYY-MM-DD HH:MM:SS) or None if parsing fails
    """
    if not date_string:
        return None

    try:
        dt = date_parser.parse(date_string)
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    except Exception as e:
        print(f"    Could not parse date '{date_string}': {e}")
        return None
