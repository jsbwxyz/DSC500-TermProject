#!/bin/bash
echo "Uploading keywords data..."
python3 app/keywords/tools/db_uploader.py

echo ""
echo "Uploading spending data..."
python3 app/spending/tools/db_uploader.py
