# Wrapper Standard

Every executable wrapper follows the same minimal factory. The goal is boring, inspectable, agent-safe execution rather than clever auto-conversion.

## Conversion steps

1. Discover public README, examples, tests, package metadata, licenses, and runtime constraints.
2. Classify domain, runtime class, dependency weight, and likely agent use cases.
3. Contract canonical input schema, output schema, error envelope, artifact names, and known limitations.
4. Add the smallest fixture that demonstrates the intended calculation or reference workflow.
5. Implement a thin adapter around public APIs or subprocess CLIs.
6. Expose a CLI command with `--input`, `--output`, `--json`, and artifact-specific outputs where useful.
7. Validate help output, manifest schema, success fixture, invalid-input envelope, and optional runtime readiness.
8. Generate or maintain agent skill docs.
9. Promote status only after evidence exists.

## CLI rules

- Shell-free argv only; no interactive prompts.
- Bounded stdout; large data goes to artifacts.
- JSON success and error envelopes on `--json`.
- Stable error codes such as `invalid_input`, `runtime_missing`, and `upstream_failure`.
- Optional R/Julia/heavy runtimes must be discoverable through `doctor` checks and skipped gracefully in tests when absent.

## Upstream rule

Adapters should call public upstream APIs/CLIs and keep any compatibility shim tiny and isolated. If a target is a GUI, book, dataset, or catalog, represent it as a reference/catalog adapter until a stable executable surface is proven.
