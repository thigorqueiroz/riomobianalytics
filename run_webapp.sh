#!/bin/bash

echo "Starting RioMobiAnalytics Web Application..."
echo "=============================================="
echo ""

export PYTHONPATH="${PYTHONPATH}:$(pwd)"

streamlit run webapp/app.py --server.port=8501 --server.address=0.0.0.0
