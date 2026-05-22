# Conversion Factory

The conversion factory is the repeatable path for turning actuarial OSS into an agent-native tool.

## Pipeline

| Step | Output |
| --- | --- |
| Discover | Notes on README/docs/examples/tests, public entrypoints, license, install/runtime constraints. |
| Classify | Domain, conversion class, priority, dependency weight, agent use cases. |
| Contract | Input schema, output schema, artifact ids, error envelope, limitations. |
| Fixture | Small input and expected output or expected reference result. |
| Adapter | Thin wrapper around public upstream API/CLI. |
| CLI | `actuary <domain> <tool>` command with file I/O and JSON envelope. |
| Validate | Help, schema, fixture, invalid input, optional runtime readiness. |
| Skill | Agent-facing usage, output interpretation, and human-review limits. |
| Promote | Evidence-based status update. |

## Conversion classes

- `python-library`: importable Python package with calculation APIs.
- `python-dsl`: Python package or CLI driven by a domain-specific declaration language.
- `python-model-runner`: model/project/template runner where directories and assumptions are inputs.
- `julia-adapter`: optional Julia subprocess/JSON bridge.
- `r-adapter`: optional Rscript subprocess/JSON bridge.
- `application-spike`: application/GUI target that needs a spike before executable wrapping.
- `reference-pack`: book, data, notebooks, or documentation used as reference/search assets.
- `catalog-importer`: registry/catalog source used to seed or update the hub.

## Priority order

Seed the full registry first, then implement P0 `chainladder-python` and `aggregate`, then P1 `cashflower` and `lifelib/modelx`, then optional R/Julia wrappers, then P3 application/reference/catalog adapters.
