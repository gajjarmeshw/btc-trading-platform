#!/bin/bash
echo "Starting BTC Trading Platform (Live Mode)..."
echo "Strategy: 1m Ultra Scalper (5 Years Trained)"
echo "---------------------------------------------"

# Check for .env
if [ ! -f .env ]; then
    echo "WARNING: .env file not found! Copying from .env.example..."
    cp .env.example .env
    echo "Please edit .env with your Binance API Keys before trading."
    exit 1
fi

# Run
python3 main.py --choice ml_1m
