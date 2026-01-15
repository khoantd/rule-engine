# Sphinx Documentation

This directory contains the Sphinx documentation for the Rule Engine.

## Building Documentation

### Prerequisites

1. **Activate virtual environment** (required):

   ```bash
   # From project root
   source .venv/bin/activate  # On macOS/Linux
   # or
   .venv\Scripts\activate     # On Windows
   ```

2. **Install development dependencies**:

   ```bash
   pip install -r requirements-dev.txt
   ```

   This will install Sphinx and the Read the Docs theme.

3. **Verify Sphinx installation**:

   ```bash
   python -m sphinx --version
   ```

### Build Documentation

**Important**: Make sure your virtual environment is activated before running make.

```bash
# From project root, activate virtual environment first
source .venv/bin/activate

# Then build documentation
cd docs
make html
```

## Troubleshooting

### Error: "No module named sphinx"

If you see `No module named sphinx`, this means Sphinx is not installed in your Python environment:

1. **Activate the virtual environment**:
   ```bash
   source ../.venv/bin/activate  # From docs directory
   # or from project root:
   source .venv/bin/activate
   ```

2. **Install development dependencies**:
   ```bash
   pip install -r ../requirements-dev.txt
   ```

3. **Verify installation**:
   ```bash
   python -m sphinx --version
   ```

4. **Try building again**:
   ```bash
   cd docs
   make html
   ```

### Error: "sphinx-build: command not found"

This is fixed in the current Makefile which uses `python -m sphinx` instead. If you still see this, ensure you're using the latest Makefile.

### Check Sphinx Installation

You can verify Sphinx is installed with:

```bash
cd docs
make check-sphinx
```

The Makefile automatically detects and uses the virtual environment Python if it exists.

The HTML documentation will be generated in `docs/_build/html/`.

### View Documentation

Open `docs/_build/html/index.html` in your browser.

### Auto-generate API Documentation

The API documentation is auto-generated from docstrings using `sphinx.ext.autodoc`.

To regenerate:

```bash
cd docs
make clean
make html
```

## Documentation Structure

- `index.rst`: Main documentation index
- `overview.rst`: System overview and architecture
- `installation.rst`: Installation instructions
- `quickstart.rst`: Quick start guide
- `configuration.rst`: Configuration guide
- `examples.rst`: Usage examples
- `api/index.rst`: API reference
- `contributing.rst`: Contributing guide

## Customizing Documentation

Edit `.rst` files and regenerate:

```bash
make html
```

## Sphinx Configuration

The Sphinx configuration is in `conf.py`. Key settings:

- **Extensions**: autodoc, viewcode, napoleon (Google-style docstrings)
- **Theme**: Read the Docs theme
- **Autodoc**: Generates API docs from docstrings

## Adding New Documentation

1. Create a new `.rst` file in `docs/`
2. Add it to `index.rst` in the toctree
3. Regenerate: `make html`

