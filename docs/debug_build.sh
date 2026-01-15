#!/bin/bash
# Debug script for Sphinx build issues

cd "$(dirname "$0")"

echo "=== Sphinx Build Debug Script ==="
echo ""

# Check Python and Sphinx
echo "1. Checking Python..."
PYTHON="../.venv/bin/python"
$PYTHON --version
echo ""

echo "2. Checking Sphinx installation..."
if ! $PYTHON -m sphinx --version > /dev/null 2>&1; then
    echo "ERROR: Sphinx not installed"
    exit 1
fi
$PYTHON -m sphinx --version
echo ""

# Check if _build/html exists
echo "3. Checking build directory..."
if [ -d "_build/html" ]; then
    echo "_build/html exists"
    ls -la _build/html/
else
    echo "_build/html does not exist - will create it"
    mkdir -p _build/html
fi
echo ""

# Try building with verbose output
echo "4. Running Sphinx build with verbose output..."
echo "Command: $PYTHON -m sphinx -b html -v -W . _build/html"
echo ""

$PYTHON -m sphinx -b html -v -W . _build/html

BUILD_EXIT=$?
echo ""
echo "Build exited with code: $BUILD_EXIT"
echo ""

# Check for output files
echo "5. Checking for output files..."
if [ -f "_build/html/index.html" ]; then
    echo "SUCCESS: index.html exists!"
    ls -lh _build/html/*.html 2>/dev/null | head -5
else
    echo "ERROR: index.html NOT found"
    if [ -d "_build/html" ]; then
        echo "Files in _build/html:"
        ls -la _build/html/
    fi
fi
echo ""

# Check for errors in conf.py
echo "6. Testing conf.py import..."
$PYTHON -c "import sys; sys.path.insert(0, '..'); exec(open('conf.py').read()); print('conf.py loaded OK')" 2>&1
echo ""

echo "=== Debug Complete ==="

