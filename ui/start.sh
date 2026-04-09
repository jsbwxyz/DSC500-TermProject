#!/bin/bash
# WigglNet UI Startup Script

cd "$(dirname "$0")"

# Use the virtual environment
VENV_PYTHON="../env/bin/python"

echo "Starting WigglNet UI Server..."
echo "Server will be available at: http://localhost:8001"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

$VENV_PYTHON main.py
