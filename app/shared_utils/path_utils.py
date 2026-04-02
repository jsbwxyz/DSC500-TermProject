"""
Path utilities for wigglnet-data-engine
Provides dynamic path resolution that works across different environments
"""

from pathlib import Path
from typing import Union


def get_project_root() -> Path:
    """
    Get the project root directory dynamically

    Returns:
        Path: Absolute path to the project root directory
    """
    # This file is in app/shared_utils/, so parent.parent.parent is the project root
    return Path(__file__).parent.parent.parent


def get_data_dir(module_name: str) -> Path:
    """
    Get the data directory for a specific module

    Args:
        module_name: Name of the module (e.g., 'article_keywords', 'product_pricing', 'disc_spending')

    Returns:
        Path: Absolute path to the module's data directory
    """
    project_root = get_project_root()
    data_dir = project_root / "app" / module_name / "data"

    # Create directory if it doesn't exist
    data_dir.mkdir(parents=True, exist_ok=True)

    return data_dir


def get_module_dir(module_name: str) -> Path:
    """
    Get the directory for a specific module

    Args:
        module_name: Name of the module (e.g., 'article_keywords', 'product_pricing', 'disc_spending')

    Returns:
        Path: Absolute path to the module directory
    """
    project_root = get_project_root()
    return project_root / "app" / module_name
