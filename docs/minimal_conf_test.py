#!/usr/bin/env python3
"""Minimal conf test to isolate issues."""
import sys
import os
import traceback

# Write directly to stderr (which should always work)
sys.stderr.write("=== MINIMAL SPHINX TEST ===\n")
sys.stderr.flush()

try:
    sys.stderr.write(f"Python: {sys.executable}\n")
    sys.stderr.write(f"Working dir: {os.getcwd()}\n")
    sys.stderr.flush()
    
    sys.path.insert(0, os.path.abspath('..'))
    
    # Test basic imports
    sys.stderr.write("Testing imports...\n")
    sys.stderr.flush()
    
    from sphinx.application import Sphinx
    sys.stderr.write("✓ Sphinx imported\n")
    sys.stderr.flush()
    
    # Test conf.py load
    sys.stderr.write("Loading conf.py...\n")
    sys.stderr.flush()
    conf_globals = {}
    exec(compile(open('conf.py').read(), 'conf.py', 'exec'), conf_globals)
    sys.stderr.write("✓ conf.py loaded\n")
    sys.stderr.flush()
    
    # Check critical config
    sys.stderr.write(f"root_doc: {conf_globals.get('root_doc', 'MISSING')}\n")
    sys.stderr.write(f"master_doc: {conf_globals.get('master_doc', 'MISSING')}\n")
    sys.stderr.flush()
    
    # Create minimal Sphinx app
    sys.stderr.write("Creating Sphinx app...\n")
    sys.stderr.flush()
    
    app = Sphinx(
        srcdir='.',
        confdir='.',
        outdir='_build/html',
        doctreedir='_build/doctrees',
        buildername='html',
        verbosity=2,
        warningiserror=False
    )
    
    sys.stderr.write("✓ App created\n")
    sys.stderr.write("Running build...\n")
    sys.stderr.flush()
    
    app.build()
    
    sys.stderr.write("✓ Build completed\n")
    sys.stderr.flush()
    
    # Check results
    if os.path.exists('_build/html/index.html'):
        size = os.path.getsize('_build/html/index.html')
        sys.stderr.write(f"✓ SUCCESS: index.html exists ({size} bytes)\n")
        sys.exit(0)
    else:
        sys.stderr.write("✗ FAILED: index.html not found\n")
        if os.path.exists('_build/html'):
            files = os.listdir('_build/html')
            sys.stderr.write(f"Files in _build/html: {files}\n")
        sys.exit(1)
        
except Exception as e:
    sys.stderr.write(f"✗ ERROR: {type(e).__name__}: {e}\n")
    traceback.print_exc(file=sys.stderr)
    sys.exit(1)

