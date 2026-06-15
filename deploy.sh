#!/bin/bash

echo "📦 Pulling latest code..."
git pull origin main

echo "🔄 Restarting service..."
sudo systemctl restart steps-app

echo "✅ Done"
