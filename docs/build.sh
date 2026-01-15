#!/bin/bash
# Build script for Sphinx documentation

set -e  # Exit on error

cd "$(dirname "$0")"

# Check if virtual environment exists
if [ ! -f "../.venv/bin/python" ]; then
    echo "Error: Virtual environment not found at ../.venv"
    echo "Please create and activate virtual environment first:"
    echo "  python3 -m venv .venv"
    echo "  source .venv/bin/activate"
    echo "  pip install -r requirements-dev.txt"
    exit 1
fi

PYTHON="../.venv/bin/python"

# Check Sphinx installation
echo "Checking Sphinx installation..."
if ! $PYTHON -m sphinx --version > /dev/null 2>&1; then
    echo "Error: Sphinx not installed"
    echo "Install with: pip install -r ../requirements-dev.txt"
    exit 1
fi

$PYTHON -m sphinx --version

# Build documentation
echo ""
echo "Building HTML documentation..."
$PYTHON -m sphinx -b html . _build/html

# Check if build succeeded
if [ -f "_build/html/index.html" ]; then
    echo ""
    echo "✓ HTML documentation built successfully!"
    echo "  Location: _build/html/index.html"
    echo ""
    echo "To view: open _build/html/index.html"
    exit 0
else
    echo ""
    echo "✗ Build failed - index.html not found"
    echo "Check for errors above"
    exit 1
fi

