#!/bin/bash
# Setup script for Document Converter API

set -e

echo "🚀 Setting up Document Converter API..."

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "❌ uv is not installed. Please install it first:"
    echo "   curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

echo "✅ uv is installed"

# Generate lock file
echo "📦 Generating lock file..."
uv lock

echo "✅ Lock file generated"

# Install dependencies
echo "📥 Installing dependencies..."
uv sync --no-install-project

echo "✅ Dependencies installed"

# Install pre-commit hooks (if in dev mode)
if [ "$1" = "--dev" ]; then
    echo "🔧 Installing pre-commit hooks..."
    uv run pre-commit install
    echo "✅ Pre-commit hooks installed"
fi

echo "🎉 Setup complete!"
echo ""
echo "Next steps:"
echo "  make dev     # Run development server"
echo "  make test    # Run tests"
echo "  make docker-build  # Build Docker image"
