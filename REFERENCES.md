# References

## Examples of good work

**Clean rule config structure** — a well-formed `rules_config.json` defines each rule with explicit `priority`, `weight`, `condition`, and `default_action`. The engine evaluates rules in priority order, accumulates `rule_point × weight`, and concatenates action results into a pattern like `"YY-"` that maps to a final recommendation like `"Approved"`. See [data/input/rules_config_v4.json](data/input/rules_config_v4.json) for the latest example.

**Dry-run execution** — calling the engine in dry-run mode returns a per-rule breakdown (`rule_id`, `matched`, `points_contributed`, `action_result`) without side effects. This is the pattern to follow when adding new execution paths: read-only, no mutations, safe in production.

**Correlation ID tracing** — every request should carry a `correlation_id` from entry point through to the execution result dict. The pattern is established in [main.py](main.py) and [services/](services/); follow it when adding new routes or Lambda handlers.

## Relevant links

- [rule-engine library docs](https://zerosteiner.github.io/rule-engine/) — the core expression evaluation library (v4.1.0) used for condition matching
- [jsonpath-ng](https://github.com/h2non/jsonpath-ng) — used for extracting values from nested input data
- [dataclasses-json](https://github.com/lidatong/dataclasses-json) — used for serialising/deserialising domain objects
- [moto](https://docs.getmoto.org/) — AWS service mocking for integration tests (S3, Lambda, etc.)
- [pytest-xdist](https://pytest-xdist.readthedocs.io/) — parallel test execution; configured in [pyproject.toml](pyproject.toml)
- [Alembic](https://alembic.sqlalchemy.org/) — database migration tool; config at [alembic.ini](alembic.ini)
- [DMN (Decision Model and Notation)](https://www.omg.org/dmn/) — standard for rule tables; parser spec at [DMN_PARSER_FEATURE.md](DMN_PARSER_FEATURE.md)
- [Chain of Responsibility pattern](https://refactoring.guru/design-patterns/chain-of-responsibility) — the multi-stage workflow orchestration pattern used in [common/pattern/cor/handler.py](common/pattern/cor/handler.py)

## Notes

- Rules and conditions belong in config files or the database — never hard-coded in Python. The config loader ([common/](common/) via `config_loader.py`) handles LRU + TTL caching and hot reload.
- The custom exception hierarchy lives in `common/exceptions.py`. Always raise typed exceptions with error codes rather than bare `Exception`.
- Three deployment targets: local script (`main.py`), AWS Lambda (`aws_main_rule_exec.py`), REST API (`run_api.py` / [api/](api/)). Each shares the same domain and service layer.
- Test coverage must stay at or above 80%. Use `moto` for AWS tests and a real DB for integration tests — do not mock the rule evaluation core.
- Code style: `black` (line length 100), `ruff`, `mypy` (strict return/unreachable checks). Config is all in [pyproject.toml](pyproject.toml).
