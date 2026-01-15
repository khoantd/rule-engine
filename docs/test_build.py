#!/usr/bin/env python3
"""Test script to build Sphinx documentation and capture all output."""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath('..'))

print("=== Starting Sphinx Build Test ===", file=sys.stderr)
print(f"Python: {sys.executable}", file=sys.stderr)
print(f"Working directory: {os.getcwd()}", file=sys.stderr)
print(f"Sphinx module location: {sys.path}", file=sys.stderr)

try:
    from sphinx.application import Sphinx
    print("✓ Sphinx module imported successfully", file=sys.stderr)
except ImportError as e:
    print(f"✗ Failed to import Sphinx: {e}", file=sys.stderr)
    sys.exit(1)

# Test configuration import
try:
    import conf
    print("✓ conf.py imported successfully", file=sys.stderr)
except Exception as e:
    print(f"✗ Failed to import conf.py: {e}", file=sys.stderr)
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Try to import modules referenced in api/index.rst
try:
    from services.ruleengine_exec import rules_exec
    print("✓ services.ruleengine_exec imported", file=sys.stderr)
except Exception as e:
    print(f"⚠ services.ruleengine_exec import failed: {e}", file=sys.stderr)

# Run Sphinx build
print("\n=== Running Sphinx Build ===", file=sys.stderr)
try:
    app = Sphinx(
        srcdir='.',
        confdir='.',
        outdir='_build/html',
        doctreedir='_build/doctrees',
        buildername='html'
    )
    app.build()
    print("✓ Build completed successfully", file=sys.stderr)
    
    # Check if output was created
    if os.path.exists('_build/html/index.html'):
        print("✓ index.html exists", file=sys.stderr)
    else:
        print("✗ index.html NOT found", file=sys.stderr)
        
except Exception as e:
    print(f"✗ Build failed: {e}", file=sys.stderr)
    import traceback
    traceback.print_exc()
    sys.exit(1)

