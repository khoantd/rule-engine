Rule Engine Documentation
==========================

Welcome to the Rule Engine documentation. This documentation provides comprehensive
information about the Rule Engine package, its architecture, APIs, and usage examples.

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   overview
   installation
   quickstart
   api/index
   configuration
   examples
   contributing

Overview
--------

The Rule Engine is a flexible and extensible framework for evaluating business rules
and workflows. It provides:

- Rule evaluation with priority-based ordering and weighted scoring
- Pattern matching for complex decision-making
- Workflow orchestration using Chain of Responsibility pattern
- Configuration management from files or AWS S3
- AWS Lambda support for serverless deployments

Key Features
~~~~~~~~~~~~

* **Rule Evaluation**: Execute business rules with priority-based ordering
* **Weighted Scoring**: Calculate weighted points based on rule matches
* **Pattern Matching**: Define action patterns for complex decisions
* **Workflow Management**: Chain workflow handlers for multi-stage processing
* **AWS Integration**: Ready-to-use Lambda handler
* **Type Safety**: Type hints throughout the codebase
* **Error Handling**: Custom exception hierarchy

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

