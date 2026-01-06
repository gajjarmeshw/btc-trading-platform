#!/bin/bash
echo "Stopping existing Trading Bot..."
pkill -f "python3 main.py" || echo "No process found."

echo "Pulling latest code..."
git pull origin main

echo "Installing requirements (just in case)..."
pip3 install -r requirements.txt

echo "Starting Trading Bot (Background Mode)..."
nohup python3 main.py > app.log 2>&1 &

echo "Deployment Complete. Logs are writing to app.log"
echo "Monitor with: tail -f app.log"
