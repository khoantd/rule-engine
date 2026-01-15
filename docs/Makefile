# Minimal makefile for Sphinx documentation
#

# You can set these variables from the command line, and also
# from the environment for the first two.
SPHINXOPTS    ?=
# Use python -m sphinx instead of sphinx-build for better reliability
# This works whether sphinx is in PATH or not, as long as it's installed

# Auto-detect virtual environment Python if it exists, otherwise use python3
VENV_PYTHON := $(shell if [ -f "../.venv/bin/python" ]; then echo "../.venv/bin/python"; elif [ -f ".venv/bin/python" ]; then echo ".venv/bin/python"; else echo ""; fi)
PYTHON       ?= $(if $(VENV_PYTHON),$(VENV_PYTHON),python3)

SPHINXBUILD  ?= $(PYTHON) -m sphinx
SOURCEDIR    = .
BUILDDIR     = _build

# Check if Sphinx is installed
check-sphinx:
	@echo "Checking Sphinx installation..."
	@if $(PYTHON) -m sphinx --version > /dev/null 2>&1; then \
		echo "✓ Sphinx is installed"; \
		$(PYTHON) -m sphinx --version; \
	else \
		echo "✗ Sphinx is NOT installed in $(PYTHON)"; \
		echo ""; \
		echo "To install Sphinx:"; \
		echo "  1. Activate virtual environment: source ../.venv/bin/activate"; \
		echo "  2. Install dependencies: pip install -r ../requirements-dev.txt"; \
		exit 1; \
	fi

# Put it first so that "make" without argument is like "make help".
help:
	@$(SPHINXBUILD) -M help "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

.PHONY: help Makefile check-sphinx

# Catch-all target: route all unknown targets to Sphinx using the new
# "make mode" option.  $(O) is meant as a shortcut for $(SPHINXOPTS).
# Before building, check if Sphinx is installed
html: check-sphinx
	@echo "Building HTML documentation..."
	@echo "Running: $(SPHINXBUILD) -b html \"$(SOURCEDIR)\" \"$(BUILDDIR)/html\""
	@$(SPHINXBUILD) -b html "$(SOURCEDIR)" "$(BUILDDIR)/html" $(SPHINXOPTS) > /tmp/sphinx_build_output.log 2>&1; \
	BUILD_EXIT=$$?; \
	echo "Build command exited with code: $$BUILD_EXIT"; \
	if [ $$BUILD_EXIT -ne 0 ]; then \
		echo ""; \
		echo "✗ Build failed with exit code: $$BUILD_EXIT"; \
		echo "Build output:"; \
		cat /tmp/sphinx_build_output.log | tail -30; \
		echo ""; \
		exit 1; \
	fi; \
	sleep 0.1; \
	if [ -f "$(BUILDDIR)/html/index.html" ]; then \
		echo ""; \
		echo "✓ HTML documentation built successfully!"; \
		echo "  Location: $(BUILDDIR)/html/index.html"; \
		echo "  Open in browser: open $(BUILDDIR)/html/index.html"; \
		WARNINGS=$$(grep -c "WARNING:" /tmp/sphinx_build_output.log 2>/dev/null || echo "0"); \
		if [ "$$WARNINGS" != "0" ]; then \
			echo "  Note: Build completed with $$WARNINGS warning(s). See /tmp/sphinx_build_output.log for details."; \
		fi; \
		exit 0; \
	else \
		echo ""; \
		echo "✗ Build failed - $(BUILDDIR)/html/index.html not found"; \
		echo "  Exit code: $$BUILD_EXIT"; \
		echo "Build output:"; \
		cat /tmp/sphinx_build_output.log | tail -30; \
		echo ""; \
		echo "  Run manually to see errors:"; \
		echo "    $(SPHINXBUILD) -b html -v -W \"$(SOURCEDIR)\" \"$(BUILDDIR)/html\""; \
		exit 1; \
	fi

%: Makefile
	@$(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

