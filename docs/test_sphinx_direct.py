#!/usr/bin/env python3
"""Direct Sphinx build test with explicit output."""
import sys
import os

def test_sphinx_direct():
    print("=== Starting Direct Sphinx Test ===", flush=True)
print(f"Python: {sys.executable}", flush=True)
print(f"Working dir: {os.getcwd()}", flush=True)
print(f"Python path: {sys.path[:3]}", flush=True)

try:
    print("\n--- Importing Sphinx ---", flush=True)
    from sphinx.application import Sphinx
    print("✓ Sphinx imported", flush=True)
    
    print("\n--- Loading conf.py ---", flush=True)
    sys.path.insert(0, os.path.abspath('..'))
    exec(compile(open('conf.py').read(), 'conf.py', 'exec'), globals())
    print("✓ conf.py loaded", flush=True)
    print(f"  root_doc: {globals().get('root_doc', 'NOT SET')}", flush=True)
    print(f"  master_doc: {globals().get('master_doc', 'NOT SET')}", flush=True)
    
    print("\n--- Creating Sphinx app ---", flush=True)
    app = Sphinx(
        srcdir='.',
        confdir='.',
        outdir='_build/html',
        doctreedir='_build/doctrees',
        buildername='html',
        verbosity=2,  # Maximum verbosity
        warningiserror=False
    )
    print("✓ Sphinx app created", flush=True)
    
    print("\n--- Running build ---", flush=True)
    app.build()
    print("✓ Build completed", flush=True)
    
    print("\n--- Checking output ---", flush=True)
    if os.path.exists('_build/html/index.html'):
        size = os.path.getsize('_build/html/index.html')
        print(f"✓ SUCCESS: index.html exists ({size} bytes)", flush=True)
        return 0
    else:
        print("✗ FAILED: index.html NOT found", flush=True)
        if os.path.exists('_build/html'):
            files = os.listdir('_build/html')
            print(f"  Files in _build/html: {files}", flush=True)
        else:
            print("  _build/html does not exist", flush=True)
            return 1
            
    except Exception as e:
        print(f"\n✗ ERROR: {type(e).__name__}: {e}", flush=True)
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(test_sphinx_direct())

