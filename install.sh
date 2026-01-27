#!/bin/bash

# Agentic Physio-Simulation Installer
# This script sets up both the Python Backend and React Frontend.

set -e # Exit on error

echo "🧬 Initializing Agentic Physio-Simulation Setup..."

# 1. Check Prerequisites
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed."
    exit 1
fi

if ! command -v npm &> /dev/null; then
    echo "❌ Node.js/npm is not installed."
    exit 1
fi

# 2. Setup Backend
echo "-----------------------------------"
echo "🐍 Setting up Python Backend..."
echo "-----------------------------------"

cd src/backend

if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate venv
source venv/bin/activate

echo "Installing Python dependencies..."
pip install -r ../../requirements.txt

# Create .env if not exists
if [ ! -f .env ]; then
    echo "Creating default .env file..."
    cp ../../.env.example .env
    echo "⚠️  IMPORTANT: Please edit src/backend/.env and add your API keys!"
fi

cd ../..

# 3. Setup Frontend
echo "-----------------------------------"
echo "⚛️  Setting up React Frontend..."
echo "-----------------------------------"

cd src/frontend

echo "Installing Node modules..."
npm install

cd ../..

echo "-----------------------------------"
echo "✅ Setup Complete!"
echo "-----------------------------------"
echo "To start the project:"
echo "1. Backend:  cd src/backend && source venv/bin/activate && python server.py"
echo "2. Frontend: cd src/frontend && npm run dev"
echo "-----------------------------------"