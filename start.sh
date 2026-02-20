#!/bin/bash

# Determine if running in development or production
if [ "$ENV" = "production" ]; then
    echo "Starting production server..."
    streamlit run app.py --server.port 8080 --server.address 0.0.0.0
else
    echo "Starting development server..."
    streamlit run app.py --server.port 8501 --server.address localhost
fi
