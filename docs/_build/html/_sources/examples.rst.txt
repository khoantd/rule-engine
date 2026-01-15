Usage Examples
==============

This page provides practical examples of using the Rule Engine.

Example 1: Simple Rule Evaluation
---------------------------------

.. code-block:: python

   from services.ruleengine_exec import rules_exec

   # Sample input data
   data = {
       'issue': 35,        # Issue number > 30
       'title': 'Superman', # Title equals 'Superman'
       'publisher': 'DC'   # Publisher in ['DC', 'Marvel']
   }

   # Execute rules
   result = rules_exec(data)

   # Result structure:
   # {
   #     'total_points': 1050.0,  # (20 * 30) + (15 * 20) + (10 * 5)
   #     'pattern_result': 'YYY', # All three rules matched
   #     'action_recommendation': 'Approved'
   # }

Example 2: Workflow Execution
-------------------------------

.. code-block:: python

   from services.workflow_exec import wf_exec

   # Execute multi-stage workflow
   result = wf_exec(
       process_name='ticket_processing',
       ls_stages=['NEW', 'INPROGESS', 'FINISHED'],
       data={
           'ticket_id': 'TICK-123',
           'title': 'Issue Report',
           'priority': 'high'
       }
   )

   # Each stage processes the data through its handler
   # The result contains the final processed data

Example 3: Custom Rule Evaluation
----------------------------------

.. code-block:: python

   from common.rule_engine_util import rule_run

   # Define a rule manually
   rule = {
       'rule_name': 'custom_rule',
       'priority': 1,
       'condition': 'issue greater_than 30',
       'rule_point': 20,
       'weight': 1.5,
       'action_result': 'Y'
   }

   # Execute single rule
   data = {'issue': 35}
   result = rule_run(rule, data)

   print(result['rule_point'])      # 20
   print(result['action_result'])    # 'Y'

Example 4: AWS Lambda Deployment
---------------------------------

Lambda Handler:

.. code-block:: python

   # lambda_handler.py
   from aws_main_rule_exec import lambda_handler

   def handler(event, context):
       """
       AWS Lambda handler.
       
       Expected event structure:
       {
           'issue': 35,
           'title': 'Superman',
           'publisher': 'DC'
       }
       """
       return lambda_handler(event, context)

Lambda Event:

.. code-block:: json

   {
     "issue": 35,
     "title": "Superman",
     "publisher": "DC"
   }

Lambda Response:

.. code-block:: json

   {
     "total_points": 1050.0,
     "pattern_result": "YYY",
     "action_recommendation": "Approved"
   }

Example 5: Error Handling
--------------------------

.. code-block:: python

   from services.ruleengine_exec import rules_exec
   from common.exceptions import DataValidationError, RuleEvaluationError

   try:
       # This will raise DataValidationError
       result = rules_exec(None)
   except DataValidationError as e:
       print(f"Validation error: {e}")
       print(f"Error code: {e.error_code}")
   except RuleEvaluationError as e:
       print(f"Evaluation error: {e}")
       print(f"Error code: {e.error_code}")

Example 6: Custom Configuration Path
--------------------------------------

.. code-block:: python

   import os
   from common.config_loader import get_config_loader

   # Set custom configuration path
   os.environ['RULES_CONFIG_PATH'] = 'custom/path/rules_config.json'

   # Load configuration
   config_loader = get_config_loader()
   rules = config_loader.load_rules_set()

Example 7: Dependency Injection
---------------------------------

.. code-block:: python

   from common.di.factory import get_handler_factory
   from services.workflow_exec import workflow_setup

   # Get handler factory
   factory = get_handler_factory()

   # Setup workflow with custom factory
   handler = workflow_setup(handler_factory=factory)

   # Use handler
   result = handler.handle('process_1', 'NEW', {'data': 'value'})

