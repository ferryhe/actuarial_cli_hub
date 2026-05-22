# Release Checklist

Use this checklist before tagging or declaring the generic conversion roadmap complete.

## Scope and repository state

- [ ] Work is in `ferryhe/actuarial_cli_hub` only.
- [ ] `main` is synced to `origin/main`.
- [ ] There are no open rollout PRs unless explicitly documented as out of scope.
- [ ] `git status --short --branch` is clean.
- [ ] Generated/runtime artifacts are absent from the diff (`build/`, `dist/`, `*.egg-info/`, `__pycache__/`, `.pytest_cache/`, `.tmp/`).

## Registry and contracts

- [ ] Every `registry/tools/*.yaml` manifest validates.
- [ ] Manifest runtime kind/status/availability matches the implemented command behavior.
- [ ] Manifest artifact ids match command success envelopes.
- [ ] Reference/catalog targets are not represented as executable calculation wrappers.
- [ ] Optional runtimes distinguish `runtime_missing`, `runtime_unavailable`, and `not_implemented`/boundary states.
- [ ] Downstream `ai_interface` exports are clearly preview-only.

## CLI and artifact behavior

- [ ] `python scripts/run_actuarial_cli.py --help` works from a sibling checkout.
- [ ] `python -m actuarial_cli_hub --help` works after editable install.
- [ ] Top-level `--help`, `registry list`, `registry validate`, and `doctor` do not import optional wrapper dependencies.
- [ ] Each implemented wrapper writes all advertised artifacts.
- [ ] Default artifacts land under `.tmp/actuarial-cli-runs/<run_id>/output/`.
- [ ] Invalid path-like `--run-id` values return JSON `invalid_input` envelopes for commands that create `RunArtifacts`.
- [ ] Bad user inputs and upstream failures produce bounded JSON errors, not tracebacks.

## Tests and validation commands

Run the release gate from the repository root:

```bash
python scripts/run_actuarial_cli.py registry validate --json
pytest -q
python scripts/run_actuarial_cli.py doctor --json
git diff --check
```

For packaging or install validation:

```bash
python -m pip install -e '.[dev]'
python -m actuarial_cli_hub --help
python scripts/run_actuarial_cli.py --help
```

Run optional runtime checks without requiring the runtime to be installed:

```bash
python scripts/run_actuarial_cli.py doctor --runtime julia --json || true
python scripts/run_actuarial_cli.py doctor --runtime r --json || true
pytest tests/integration_optional -q
```

## Review and release notes

- [ ] Run Codex review before commit/PR: `codex -c 'model="gpt-5.5"' review --uncommitted`.
- [ ] Fix only technically correct, in-scope findings.
- [ ] Re-run focused and full validation after review fixes.
- [ ] PR body lists exact validation commands and their result.
- [ ] After PR creation/update, wait about 15 minutes and check `gh pr view`, pull review comments API, GraphQL review threads, and `gh pr checks`.
- [ ] Resolve only comments that are truly fixed or outdated.
- [ ] Squash merge only when merge state is clean, checks are green or absent, and no actionable comments remain.
