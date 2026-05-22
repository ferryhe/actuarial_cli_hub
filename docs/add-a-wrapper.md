# Add an Actuarial Wrapper

Use this playbook when converting another actuarial open-source project into an `actuary ...` command. Keep the wrapper thin, evidence-based, and agent-safe.

## 1. Discover

Record the upstream facts before writing code:

- Repository, package name, license, and install command.
- Public API, CLI, notebook, or documented examples to call.
- Runtime class: Python library, Python DSL, optional Python runtime, R/Julia bridge, application spike, reference pack, or catalog source.
- Smallest useful actuarial example and required input data.
- Known limitations and where qualified actuarial review is required.

Do not modify upstream projects or downstream consumers as part of a hub wrapper PR.

## 2. Classify and choose the right shape

Not every target becomes an executable calculation command.

| Target shape | Use when | CLI pattern |
| --- | --- | --- |
| Full Python wrapper | Public Python API can run a deterministic fixture in CI. | `actuary <domain> <tool> --input ... --output ... --json` |
| Optional runtime boundary | Heavy Python/R/Julia runtime may be absent in base CI. | Command returns `runtime_missing`, `runtime_unavailable`, or `not_implemented` until fixture-backed execution exists. |
| Subprocess JSON bridge | R/Julia/CLI process exchanges JSON files/stdout. | Enforce timeout and output caps while the child is running. |
| Reference/catalog adapter | GUI, book, dataset, or catalog is useful but not a calculation engine. | Emit `reference_result` or `run_manifest` artifacts; no runtime execution claims. |

## 3. Define the contract first

Before implementing the adapter, define:

- Tool id, status, runtime kind, availability, and priority in `registry/tools/<tool>.yaml`.
- Conversion metadata required by the manifest schema: `conversion.class`, `conversion.form`, `conversion.dependencyWeight`, and `conversion.readiness` when useful.
- Input and output schemas under `registry/schemas/` when a new domain shape is needed.
- Artifact ids and filenames. Keep success envelopes and registry declarations in lockstep.
- Error envelopes and codes: use `invalid_input`, `runtime_missing`, `runtime_unavailable`, `not_implemented`, or `upstream_failure` as appropriate.
- Default run root: `.tmp/actuarial-cli-runs/<run_id>/output/`.

## 4. Implement the smallest adapter

1. Copy `templates/adapter/adapter.py` into `src/actuarial_cli_hub/adapters/<tool>.py`.
2. Keep upstream imports lazy inside adapter functions or command handlers.
3. Add a subcommand in `src/actuarial_cli_hub/cli.py`.
4. Catch user/input/runtime errors and return bounded JSON envelopes with `--json`.
5. Write outputs to explicit paths or to the canonical run root.
6. Avoid shell invocation. Use argv lists for subprocesses.

## 5. Add tests before promotion

Start from `templates/tests/test_tool_cli.py` and add at least:

- Help output test.
- Manifest validation test.
- Happy-path fixture test when the wrapper is executable.
- JSON failure-path test for invalid input.
- Runtime-missing/unavailable tests for optional runtimes, using monkeypatch or probe fakes rather than requiring R/Julia/heavy packages in base CI.
- Artifact path collision/default-path regression when the command writes multiple artifacts.

Do not mark a tool `experimental` or `availability: implemented` until both happy-path and failure-path tests pass.

## 6. Generate skills/tool cards when registry metadata changes

If the wrapper should appear in generated agent-facing artifacts, fix the generator first and regenerate checked-in outputs:

```bash
python scripts/run_actuarial_cli.py skills export --target generic --output skills/generic --json
python scripts/run_actuarial_cli.py skills export --target ai_interface --output skills/ai_interface/actuarial_cli_hub --json
```

Keep `ai_interface` exports preview-only unless a separate downstream PR wires them in.

## 7. Validate the PR

Run the commands relevant to the wrapper plus the repository release gate:

```bash
python scripts/run_actuarial_cli.py registry validate --json
pytest -q
python scripts/run_actuarial_cli.py doctor --json
git diff --check
codex -c 'model="gpt-5.5"' review --uncommitted
```

Clean generated artifacts (`build/`, `*.egg-info/`, `__pycache__/`, `.pytest_cache/`, `.tmp/`) before committing.
