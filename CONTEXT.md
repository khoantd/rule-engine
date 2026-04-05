# Current Project

## What we are building

A flexible, extensible Python rule engine framework for evaluating business rules dynamically against input data. It calculates weighted scores from prioritised rules, matches result patterns to action recommendations, and supports multi-stage workflow orchestration via a Chain of Responsibility pattern. The engine runs locally, as an AWS Lambda function, or as a REST API, and stores rules in JSON files, AWS S3, or PostgreSQL/TimescaleDB.

## What good looks like

- Rules are loaded from config (JSON, DMN, or database), validated, and executed in priority order against input data
- Each matched rule contributes `rule_point × weight` to a cumulative score; unmatched rules contribute their default action result (e.g. `"-"` or `"N"`)
- Concatenated action results form a pattern string (e.g. `"YY-"`) that maps to a final action recommendation (e.g. `"Approved"`)
- The execution result is a clean dict: `{ total_points, pattern_result, action_recommendation, correlation_id, execution_time_ms }`
- Dry-run mode returns a detailed per-rule evaluation breakdown without side effects
- Batch execution runs concurrently across a configurable worker pool
- Config is cached (LRU + TTL) and hot-reloadable without a server restart
- All requests carry a correlation ID for end-to-end distributed tracing
- Unit and integration test coverage stays at or above 80%

## What to avoid

- Do not bypass the caching layer by loading rule configs on every call — always go through `config_loader.py`
- Do not hard-code rule logic in application code; rules and conditions belong in config files or the database, not Python
- Do not add execution side effects inside dry-run mode; it must remain read-only and safe to call in production
- Do not conflate the service layer (`services/`) with domain objects (`domain/`) — keep business logic in the domain and orchestration in services
- Do not ignore the custom exception hierarchy in `common/exceptions.py`; raise specific typed exceptions with error codes rather than generic `Exception`
- Do not skip correlation IDs when adding new execution paths; every request must be traceable end-to-end
- Do not write tests that mock the rule evaluation core when integration tests are more appropriate — moto is available for AWS, and a real DB can be used for integration tests
