#!/usr/bin/env python3
"""Minimal test to debug Sphinx build."""
import sys
import os

# Redirect output to file
log_file = open('sphinx_test.log', 'w')
sys.stdout = log_file
sys.stderr = log_file

print("=== Starting Sphinx Test ===", flush=True)
print(f"Python: {sys.executable}", flush=True)
print(f"Working dir: {os.getcwd()}", flush=True)

try:
    from sphinx.application import Sphinx
    print("✓ Sphinx imported", flush=True)
    
    # Try to build
    app = Sphinx(
        srcdir='.',
        confdir='.',
        outdir='_build/html',
        doctreedir='_build/doctrees',
        buildername='html'
    )
    print("✓ Sphinx app created", flush=True)
    
    app.build()
    print("✓ Build completed", flush=True)
    
    # Check output
    if os.path.exists('_build/html/index.html'):
        print("✓ index.html exists!", flush=True)
        print(f"  Size: {os.path.getsize('_build/html/index.html')} bytes", flush=True)
    else:
        print("✗ index.html NOT found", flush=True)
        if os.path.exists('_build/html'):
            print(f"  _build/html exists: {os.listdir('_build/html')}", flush=True)
        else:
            print("  _build/html does not exist", flush=True)
            
except Exception as e:
    print(f"✗ Error: {e}", flush=True)
    import traceback
    traceback.print_exc(file=log_file)
finally:
    log_file.close()

print("Check sphinx_test.log for output", file=sys.__stdout__)

