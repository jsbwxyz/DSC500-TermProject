"""
Web scraping utilities for wigglnet-data-engine
Consolidates common web scraping configuration and utilities
"""

from selenium.webdriver.chrome.options import Options
from typing import Dict


def create_chrome_options() -> Options:
    """
    Create standardized Chrome options for headless browsing

    Returns:
        Options: Configured Chrome options object
    """
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    return chrome_options


def get_standard_headers() -> Dict[str, str]:
    """
    Get standardized HTTP request headers

    Returns:
        dict: Headers dictionary with User-Agent
    """
    return {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
