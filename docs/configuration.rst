Configuration Guide
===================

The Rule Engine uses JSON configuration files to define rules and patterns.

Rule Configuration
------------------

Rules are defined in JSON format. The default location is
``data/input/rules_config.json`` (or ``rules_config_v4.json``).

Configuration Structure
-----------------------

.. code-block:: json

   {
     "rules_set": [
       {
         "id": "R0001",
         "rule_name": "Rule 1",
         "attribute": "issue",
         "condition": "greater_than",
         "constant": "30",
         "message": "the issue is greater than 30",
         "weight": 30,
         "rule_point": 20,
         "priority": 1,
         "action_result": "Y"
       }
     ],
     "patterns": {
       "YYY": "Approved",
       "Y--": "Rejected",
       "YY-": "Reviewed"
     }
   }

Rule Fields
-----------

- **id**: Unique rule identifier
- **rule_name**: Human-readable rule name
- **attribute**: Data attribute to evaluate
- **condition**: Condition operator (see supported operators below)
- **constant**: Constant value for comparison
- **weight**: Weight multiplier for scoring
- **rule_point**: Base points awarded when rule matches
- **priority**: Execution priority (lower = higher priority)
- **action_result**: Result character (e.g., "Y", "N", "-")

Pattern Fields
--------------

- **Keys**: Pattern strings (e.g., "YYY", "Y--")
- **Values**: Action recommendations (e.g., "Approved", "Rejected")

Condition Operators
-------------------

Supported condition operators:

- ``equal``: Equality check (==)
- ``not_equal``: Inequality check (!=)
- ``greater_than``: Greater than (>)
- ``greater_than_or_equal``: Greater than or equal (>=)
- ``less_than``: Less than (<)
- ``less_than_or_equal``: Less than or equal (<=)
- ``in``: Membership check (in)
- ``not_in``: Non-membership check (not in)
- ``range``: Range check (in [list])
- ``contains``: String contains
- ``regex``: Regular expression match

Environment Configuration
-------------------------

Configuration can be overridden via environment variables:

.. code-block:: bash

   # Configuration file paths
   export RULES_CONFIG_PATH=data/input/rules_config_v4.json
   export CONDITIONS_CONFIG_PATH=data/input/conditions_config.json

   # AWS Configuration
   export AWS_REGION=us-east-1
   export S3_BUCKET=my-config-bucket
   export S3_CONFIG_PREFIX=config/

   # Environment
   export ENVIRONMENT=production

Configuration Sources
---------------------

The engine supports multiple configuration sources:

1. **Local Files**: Default configuration from ``data/input/``
2. **AWS S3**: Load configurations from S3 buckets
3. **Environment Variables**: Override specific settings

Using S3 Configuration
-----------------------

.. code-block:: python

   from common.s3_aws_util import aws_s3_config_file_read

   # Read from S3
   config = aws_s3_config_file_read(
       bucket='my-config-bucket',
       key='config/rules_config.json'
   )

Configuration Caching
---------------------

Configuration is automatically cached for performance:

- Rules configuration is cached after first load
- Conditions configuration is cached
- Actions/patterns configuration is cached

Reloading Configuration
-----------------------

To force reload configuration:

.. code-block:: python

   from common.config_loader import get_config_loader

   config_loader = get_config_loader()
   config_loader.clear_cache()  # Clear cache
   rules = config_loader.load_rules_set()  # Reload

