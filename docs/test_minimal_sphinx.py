#!/usr/bin/env python3
"""Test with absolute minimal configuration."""
import sys
import os

# Force unbuffered output
sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', buffering=1)
sys.stderr = os.fdopen(sys.stderr.fileno(), 'w', buffering=1)

print("=== MINIMAL SPHINX TEST ===", file=sys.stderr)
print(f"Python: {sys.executable}", file=sys.stderr)
print(f"cwd: {os.getcwd()}", file=sys.stderr)

try:
    sys.path.insert(0, os.path.abspath('..'))
    
    print("Importing Sphinx...", file=sys.stderr)
    from sphinx.application import Sphinx
    print("OK", file=sys.stderr)
    
    # Create minimal config dict
    print("Creating minimal config...", file=sys.stderr)
    config = {
        'project': 'Test',
        'root_doc': 'index',
        'master_doc': 'index',
        'extensions': [],  # NO extensions
    }
    print("OK", file=sys.stderr)
    
    print("Creating Sphinx app...", file=sys.stderr)
    app = Sphinx(
        srcdir='.',
        confdir='.',
        outdir='_build/html',
        doctreedir='_build/doctrees',
        buildername='html',
        confoverrides=config,
        verbosity=2,
        warningiserror=False,
        status=sys.stderr,
        warning=sys.stderr,
    )
    print("OK", file=sys.stderr)
    
    print("Building...", file=sys.stderr)
    app.build()
    print("Done", file=sys.stderr)
    
    if os.path.exists('_build/html/index.html'):
        print("SUCCESS!", file=sys.stderr)
        sys.exit(0)
    else:
        print("FAILED - no index.html", file=sys.stderr)
        sys.exit(1)
        
except Exception as e:
    print(f"ERROR: {e}", file=sys.stderr)
    import traceback
    traceback.print_exc(file=sys.stderr)
    sys.exit(1)

