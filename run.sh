#!/bin/bash
set -e

echo "Starting Qdrant..."
./qdrant & sleep 5

echo "Building Knowledge Base..."
python kb/build_local_kb.py

echo "Launching QuantumShield..."
streamlit run ui/app.py \
    --server.port 7860 \
    --server.address 0.0.0.0 \
    --server.enableCORS false \
    --server.enableXsrfProtection false