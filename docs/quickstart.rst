Quick Start Guide
=================

This guide will help you get started with the Rule Engine quickly.

Basic Rule Execution
--------------------

The simplest way to use the Rule Engine:

.. code-block:: python

   from services.ruleengine_exec import rules_exec

   # Define input data
   data = {
       'issue': 35,
       'title': 'Superman',
       'publisher': 'DC'
   }

   # Execute rules
   result = rules_exec(data)

   # Access results
   print(f"Total Points: {result['total_points']}")
   print(f"Pattern Result: {result['pattern_result']}")
   print(f"Action Recommendation: {result['action_recommendation']}")

Result Structure
----------------

The ``rules_exec`` function returns a dictionary with:

- ``total_points``: Sum of weighted rule points
- ``pattern_result``: Concatenated action results (e.g., "YYY")
- ``action_recommendation``: Recommended action based on pattern

Workflow Execution
------------------

Execute multi-stage workflows:

.. code-block:: python

   from services.workflow_exec import wf_exec

   result = wf_exec(
       process_name='process_1',
       ls_stages=['NEW', 'INPROGESS', 'FINISHED'],
       data={'id': 1, 'name': 'John', 'dob': '01/01/1990'}
   )

AWS Lambda Usage
----------------

Use the Lambda handler for serverless deployments:

.. code-block:: python

   from aws_main_rule_exec import lambda_handler

   # Lambda event
   event = {
       'issue': 35,
       'title': 'Superman',
       'publisher': 'DC'
   }

   # Execute via Lambda handler
   result = lambda_handler(event, context=None)

Next Steps
----------

- Read the :doc:`configuration` guide
- Explore the :doc:`api/index` documentation
- Check out :doc:`examples` for more use cases

