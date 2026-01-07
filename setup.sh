#!/bin/bash

# HelloSales Quick Setup Script

set -e

echo "🚀 Setting up HelloSales..."
echo ""

# Check prerequisites
command -v docker >/dev/null 2>&1 || { echo "❌ Docker is not installed. Please install Docker first."; exit 1; }
command -v docker-compose >/dev/null 2>&1 || command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1 || { echo "❌ Docker Compose is not installed. Please install Docker Compose first."; exit 1; }
command -v python3 >/dev/null 2>&1 || { echo "❌ Python 3 is not installed. Please install Python 3.11+ first."; exit 1; }
command -v node >/dev/null 2>&1 || command -v nodejs >/dev/null 2>&1 || { echo "❌ Node.js is not installed. Please install Node.js 18+ first."; exit 1; }

echo "✅ Prerequisites check passed"
echo ""

# Start infrastructure
echo "📦 Starting infrastructure (PostgreSQL, Redis)..."
make up
echo ""

# Install backend dependencies
echo "🐍 Installing backend dependencies..."
cd backend
pip install -e ".[dev]"
cd ..
echo ""

# Setup environment file
echo "⚙️  Setting up environment..."
if [ ! -f backend/.env ]; then
    cp backend/.env.example backend/.env
    echo "✅ Created backend/.env from .env.example"
    echo "⚠️  Please edit backend/.env with your API keys"
else
    echo "ℹ️  backend/.env already exists"
fi
echo ""

# Install mobile dependencies
echo "📱 Installing mobile dependencies..."
cd mobile
npm install
cd ..
echo ""

echo "✨ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit backend/.env with your API keys"
echo "2. Run: make migrate-db"
echo "3. Run: make backend   (in one terminal)"
echo "4. Run: make mobile    (in another terminal)"
echo ""
echo "For more information, see README.md or QUICKSTART.md"
