Installation
=============

Prerequisites
-------------

- Python 3.8 or higher
- pip package manager

Installation Steps
------------------

1. **Clone the repository**:

   .. code-block:: bash

      git clone <repository-url>
      cd rule_engine

2. **Create virtual environment**:

   .. code-block:: bash

      python -m venv .venv

3. **Activate virtual environment**:

   On macOS/Linux:
   
   .. code-block:: bash

      source .venv/bin/activate

   On Windows:
   
   .. code-block:: bash

      .venv\Scripts\activate

4. **Install dependencies**:

   .. code-block:: bash

      pip install -r requirements.txt

Development Installation
------------------------

For development with all testing and linting tools:

.. code-block:: bash

   pip install -r requirements-dev.txt

Or using pyproject.toml:

.. code-block:: bash

   pip install -e ".[dev]"

Verifying Installation
----------------------

Test the installation:

.. code-block:: python

   from services.ruleengine_exec import rules_exec
   result = rules_exec({'test': 'data'})
   print(result)

Requirements
------------

Core Dependencies
~~~~~~~~~~~~~~~~~

- ``rule-engine>=4.1.0``: Core rule engine library
- ``jsonpath_ng>=1.5.3``: JSON path utilities
- ``dataclasses-json>=0.6.6``: Data class JSON serialization

Development Dependencies
~~~~~~~~~~~~~~~~~~~~~~~~~

See ``requirements-dev.txt`` for complete list:

- pytest: Testing framework
- black: Code formatting
- mypy: Type checking
- flake8: Linting
- sphinx: Documentation generation

