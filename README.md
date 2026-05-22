# actuarial_cli_hub

`actuarial_cli_hub` is a contract-first hub for turning actuarial open-source software into agent-native CLI tools. Its job is to provide a stable layer of registries, schemas, adapters, examples, artifacts, and skills around upstream actuarial projects so humans and AI agents can run actuarial workflows through predictable file/CLI contracts.

This repository is not an `ai_interface` subproject. `ai_interface` is one downstream consumer used to sanity-check the contracts; implementation work here should stay inside this repo unless a separate downstream integration task explicitly says otherwise.

## Product shape

```text
Registry -> Domain Schema -> Adapter -> CLI Command -> Artifact Contract -> Golden Fixture -> Skill Pack
```

The hub starts with a curated registry of actuarial OSS targets and promotes each target only when evidence exists:

| Status | Meaning |
| --- | --- |
| `cataloged` | Known project listed in the registry with URL, domain, language, and install notes. |
| `manifested` | Machine-readable manifest exists and validates. |
| `fixture-ready` | Minimal example inputs and schema drafts exist. |
| `experimental` | CLI command runs locally with success and error-envelope tests. |
| `stable` | Safe default for agents after golden tests, docs, limitations, and readiness checks. |
| `external-reference` | Useful knowledge/catalog source rather than an executable calculation wrapper. |

## Initial target map

The initial registry intentionally covers several conversion classes before runtime wrappers are implemented:

- P0 Python wrappers: `chainladder-python`, `aggregate`.
- P1 Python model runners: `cashflower`, `lifelib`, `modelx`.
- P2 optional cross-runtime adapters: JuliaActuary / `MortalityTables.jl`, R `lifecontingencies`, R `insurancerating`.
- P3 app/reference/catalog assets: `FASLR`, Loss Data Analytics materials, `actuarial-foss`.

## v1 non-goals

- No rewrite or vendoring of upstream actuarial libraries.
- No dependency on `ai_interface` TypeScript internals.
- No long-running HTTP service or MCP server in v1.
- No regulatory-production readiness claim.
- No automatic conversion claim before the manual conversion factory is proven.

## Repository roadmap

The current roadmap lives in [`docs/plans/2026-05-21-generic-conversion-roadmap.md`](docs/plans/2026-05-21-generic-conversion-roadmap.md). The first milestone is documentation plus registry taxonomy only; runtime commands come later.

## Current validation

Use the repo-local script from a sibling checkout, or `python -m actuarial_cli_hub` after installation:

```bash
python scripts/run_actuarial_cli.py registry validate --json
pytest -q
python scripts/run_actuarial_cli.py doctor --json
git diff --check
```

For new wrappers, follow [`docs/add-a-wrapper.md`](docs/add-a-wrapper.md). For release readiness, use [`docs/release-checklist.md`](docs/release-checklist.md).
