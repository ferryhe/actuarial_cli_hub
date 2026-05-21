# actuarial_cli_hub × ai_interface Integration Roadmap

> **For Hermes/Codex implementers:** this is a planning document only. Do not modify `ferryhe/ai_interface` as part of the `actuarial_cli_hub` implementation PRs. Treat `ai_interface` as a read-only integration target until a later explicitly scoped PR is opened in that repo.

**Date:** 2026-05-21

**Repos:**
- Runtime/tooling repo: `https://github.com/ferryhe/actuarial_cli_hub`
- Read-only integration target inspected for compatibility: `https://github.com/ferryhe/ai_interface`

---

## 1. Executive Summary

`actuarial_cli_hub` should become the domain-specific, agent-native runtime layer for actuarial open-source tools. It should **not** absorb `ai_interface`, and `ai_interface` should **not** directly import actuarial calculation libraries such as `chainladder`, `aggregate`, `cashflower`, `lifelib`, R packages, or Julia packages.

The clean architecture is:

```text
ai_interface
  -> loads skill/tool manifests
  -> invokes safe CLI adapters
  -> stores and renders run artifacts, events, logs, and JSON/Markdown outputs

actuarial_cli_hub
  -> owns actuarial CLI entrypoints, registry manifests, schemas, fixtures, skills, and adapters
  -> invokes upstream actuarial OSS libraries behind stable CLI/file contracts

upstream actuarial OSS
  -> chainladder-python, aggregate, cashflower, lifelib/modelx, JuliaActuary, R actuarial packages
```

This makes `actuarial_cli_hub` independently useful as a CLI package while making it easy for `ai_interface` to consume through its existing safe CLI executor, skill manifest, and artifact viewer. Step-level DAG/pipeline visualization in `ai_interface` should be treated as a later enhancement, not as a v1 zero-change integration guarantee.

---

## 2. Read-only Findings from `ai_interface`

The current `ai_interface` structure already fits the proposed integration model. Relevant observed facts:

1. `ai_interface` is a top-level Agent OS console for skills/tools, with foreground agent flow and Backstage inspection.
2. It loads YAML skill manifests from:
   - `skills/builtin`
   - `skills/community`
   - `skills/custom`
3. Existing built-in skills include `ai_actuary`, which already uses a **CLI + artifact** boundary instead of TypeScript actuarial logic.
4. `skills/builtin/ai_actuary/skill.yaml` declares:
   - `execution.kind: cli`
   - `command: [python, scripts/run_tool_pipeline.py, --json]`
   - `workingDirectory: project`
   - allowlisted command prefix: `python scripts/run_tool_pipeline.py`
   - project path fallback: `../ai_actuary`
5. `artifacts/api-server/src/tool-adapters/cli-executor.ts` supports bounded CLI execution with:
   - safe `spawn` usage, no shell;
   - command allowlists;
   - timeout and max-output caps;
   - project fallback path detection;
   - stdout/stderr capture and secret/path redaction.
6. `artifacts/api-server/src/pipelines/manifest.ts` already defines an actuarial pipeline manifest shape:

```ts
interface ActuarialPipelineStepManifest {
  id: string;
  toolId: string;
  when?: string;
  inputs: Record<string, string>;
  outputs: Record<string, string>;
}

interface ActuarialPipelineManifest {
  pipelineId: string;
  version: string;
  artifactRoot: string;
  steps: ActuarialPipelineStepManifest[];
}
```

7. `artifacts/api-server/src/pipelines/actuarial-reserving-review.yaml` already models a reserving pipeline as artifact steps:

```text
case_input.json
  -> chainladder-calc -> deterministic_result.json
  -> narrative-draft -> narrative_draft.json
  -> constitution-check -> constitution_check.json
  -> review-generator -> review_packet.json/md
  -> report-export -> operator_handoff.md + reserve_summary.*
```

**Implication:** the first integration path should be a CLI/file contract modeled after the existing `ai_actuary` pattern. No HTTP service or MCP server is needed for the first version. However, `ai_interface` currently hard-codes sibling project fallback mappings for specific modules such as `ai_actuary` and `climate_monitor`; a future `ai_interface` PR is still required before `actuarial_cli_hub` becomes a first-class executable skill there.

---

## 3. Product Definition

### 3.1 One-line Positioning

**`actuarial_cli_hub` makes actuarial open-source software agent-native through stable CLI contracts, schemas, examples, registries, and skills.**

### 3.2 Non-goals for v1

- Do not rewrite upstream actuarial libraries.
- Do not embed `ai_interface` code or depend on its TypeScript internals.
- Do not expose a long-running HTTP service in v1.
- Do not expose MCP in v1.
- Do not claim regulatory-production readiness.
- Do not attempt automatic wrapper generation for every actuarial repo before the manual contracts prove useful.

### 3.3 Target Users

1. **Actuarial practitioners** who want reproducible command-line workflows for reserving, aggregate loss, mortality, cash-flow, or IFRS 17 experiments.
2. **AI agents** that need predictable, bounded, artifact-based tool calls.
3. **`ai_interface`** as an orchestration/UI layer that needs skills and tool manifests it can inspect, execute, and display.
4. **Open-source actuarial contributors** who want a standard way to make their packages consumable by agents.

---

## 4. Architecture

### 4.1 Runtime Layers

```text
┌───────────────────────────────────────────────────────────┐
│ ai_interface                                               │
│ - skill catalog                                            │
│ - safe CLI/HTTP/MCP executors                              │
│ - Backstage run inspection                                 │
│ - user approvals, artifacts, logs, JSON/Markdown renderers │
└───────────────────────────┬───────────────────────────────┘
                            │ CLI/file contract
                            ▼
┌───────────────────────────────────────────────────────────┐
│ actuarial_cli_hub                                          │
│ - `actuary` CLI                                             │
│ - registry/tool manifests                                  │
│ - JSON Schemas and Pydantic contracts                      │
│ - adapter modules for upstream OSS                         │
│ - fixtures/golden outputs                                  │
│ - generated agent skills / ai_interface manifests          │
└───────────────────────────┬───────────────────────────────┘
                            │ package/runtime adapters
                            ▼
┌───────────────────────────────────────────────────────────┐
│ Upstream actuarial OSS                                     │
│ - casact/chainladder-python                                │
│ - mynl/aggregate                                           │
│ - acturtle/cashflower                                      │
│ - lifelib-dev/lifelib + fumitoh/modelx                     │
│ - JuliaActuary packages                                    │
│ - R packages such as lifecontingencies / insurancerating   │
└───────────────────────────────────────────────────────────┘
```

### 4.2 Adapter Pattern

Every supported tool should follow this layering:

```text
upstream library call
  -> pure Python adapter function
  -> CLI command with JSON/file I/O
  -> registry manifest
  -> JSON Schema
  -> golden fixture
  -> agent skill / ai_interface skill manifest
```

Do not duplicate business logic between CLI, future HTTP, and future MCP adapters. The stable core should be the pure adapter function plus Pydantic contracts.

### 4.3 File/Artifact Contract

The CLI should always support explicit artifact paths:

```bash
actuary reserve chainladder \
  --input examples/reserving/sample_triangle.csv \
  --output .tmp/runs/demo/deterministic_result.json \
  --diagnostics-output .tmp/runs/demo/diagnostics.json \
  --explain-output .tmp/runs/demo/explanation.md \
  --json
```

Recommended run layout:

```text
.tmp/actuarial-cli-runs/<run_id>/
  manifest.json
  input/
    case_input.json
    triangle.csv
  output/
    deterministic_result.json
    diagnostics.json
    explanation.md
  logs/
    stdout.log
    stderr.log
```

The CLI should return a concise JSON envelope on stdout:

```json
{
  "ok": true,
  "status": "ok",
  "tool_id": "actuarial.reserve.chainladder",
  "version": "actuarial-reserving.v1",
  "run_id": "demo",
  "artifact_root": ".tmp/actuarial-cli-runs/demo",
  "artifacts": {
    "deterministic_result": "output/deterministic_result.json",
    "diagnostics": "output/diagnostics.json",
    "explanation": "output/explanation.md"
  },
  "warnings": []
}
```

Failures should also be JSON and should not rely on traceback parsing:

```json
{
  "ok": false,
  "status": "error",
  "tool_id": "actuarial.reserve.chainladder",
  "error": {
    "code": "invalid_triangle",
    "message": "Input triangle must contain origin, development, and value columns.",
    "recoverable": true,
    "details": []
  }
}
```

---

## 5. Proposed Repository Structure

```text
actuarial_cli_hub/
  README.md
  pyproject.toml
  src/
    actuarial_cli_hub/
      __init__.py
      cli.py
      contracts/
        __init__.py
        base.py
        reserving.py
        aggregate_loss.py
        mortality.py
      adapters/
        __init__.py
        chainladder_adapter.py
        aggregate_adapter.py
        cashflower_adapter.py
        lifelib_adapter.py
        julia_mortality_adapter.py
      commands/
        __init__.py
        reserve.py
        loss.py
        mortality.py
        life.py
      registry/
        loader.py
        validator.py
      skills/
        generator.py
  registry/
    tools/
      chainladder-python.yaml
      aggregate.yaml
      cashflower.yaml
      lifelib.yaml
      mortalitytables-jl.yaml
    domains/
      reserving.yaml
      aggregate_loss.yaml
      life_modeling.yaml
      mortality.yaml
    schemas/
      tool-manifest.schema.json
      reserving-triangle.schema.json
      reserving-result.schema.json
      error-envelope.schema.json
  skills/
    hermes/
      actuarial-reserving/SKILL.md
      actuarial-aggregate-loss/SKILL.md
      actuarial-mortality/SKILL.md
    ai_interface/
      actuarial_cli_hub/skill.yaml
  examples/
    reserving/
      sample_triangle.csv
      case_input.json
      expected_result.json
    aggregate_loss/
      simple_decl.yaml
      expected_result.json
  tests/
    test_cli_help.py
    test_registry_contracts.py
    test_chainladder_cli.py
    test_error_envelopes.py
  docs/
    architecture.md
    wrapper-standard.md
    agent-skill-standard.md
    ai-interface-integration.md
    plans/
      2026-05-21-ai-interface-integration-roadmap.md
```

---

## 6. Tool Manifest Standard v1

Each tool manifest should be machine-readable and portable across `actuarial_cli_hub`, `ai_interface`, and future MCP/HTTP adapters.

Example for `chainladder-python`:

```yaml
id: actuarial.reserve.chainladder
version: actuarial-reserving.v1
name: Chainladder Reserving
status: experimental
category: reserving
upstream:
  repo: https://github.com/casact/chainladder-python
  package: chainladder
  language: python
runtime:
  kind: cli
  command:
    - actuary
    - reserve
    - chainladder
  allowedCommandPrefix: actuary reserve chainladder
  timeoutMs: 300000
  maxOutputBytes: 1048576
io:
  inputSchema: registry/schemas/reserving-triangle.schema.json
  outputSchema: registry/schemas/reserving-result.schema.json
  artifacts:
    - deterministic_result
    - diagnostics
    - explanation_markdown
agent:
  skillPath: skills/hermes/actuarial-reserving/SKILL.md
  useCases:
    - P&C loss reserving methodology validation
    - triangle diagnostics
    - reserving demo or teaching workflow
  limitations:
    - Not a regulatory-production reserving system
    - Requires actuarial review before business use
ai_interface:
  suggestedSkillId: actuarial_cli_hub
  defaultSiblingPath: ../actuarial_cli_hub
  envPath: ACTUARIAL_CLI_HUB_PROJECT_PATH
```

---

## 7. `ai_interface` Integration Contract

### 7.1 Integration Shape

The first integration should be a single `ai_interface` skill manifest that points at `actuarial_cli_hub` as a sibling project. **Important constraint:** in the current `ai_interface` implementation, sibling project fallback is not fully manifest-driven. `project.defaultSiblingPath` is metadata, but executable fallback currently becomes reliable only when `ai_interface` maps a module to a `projectFallback.requiredPath` in code. Therefore, the manifest below is a **preview/handoff manifest**, not a claim that copying it into `ai_interface` will work without a later `ai_interface` PR.

The recommended v1 execution model is to mimic `ai_actuary`: use a repo-local script that can bootstrap `src/` layout imports from a sibling checkout. This avoids assuming that `actuarial_cli_hub` has already been installed editable in the Python environment used by `ai_interface`.

```yaml
skillId: actuarial_cli_hub
moduleId: actuarial_cli_hub
name: Actuarial CLI Hub
description: Invoke actuarial open-source tools through the actuarial_cli_hub CLI and inspect JSON/Markdown artifacts.
category: agent
project:
  source: builtin
  defaultSiblingPath: ../actuarial_cli_hub
  envPath: ACTUARIAL_CLI_HUB_PROJECT_PATH
  repoUrl: https://github.com/ferryhe/actuarial_cli_hub
  packageName: actuarial_cli_hub
execution:
  kind: cli
  adapterId: actuarial_cli_hub.cli.v1
  requiredEnv:
    - ACTUARIAL_CLI_HUB_PROJECT_PATH
  optionalEnv:
    - ACTUARIAL_CLI_HUB_PYTHON
  command:
    - python
    - scripts/run_actuarial_cli.py
    - --json
  workingDirectory: project
  allowedCommands:
    - python scripts/run_actuarial_cli.py
  timeoutMs: 300000
  maxOutputBytes: 1048576
  supportsResume: false
  readinessHint: Set ACTUARIAL_CLI_HUB_PROJECT_PATH to the actuarial_cli_hub repo root. A later ai_interface PR must add a projectFallback mapping, or users must configure the env path explicitly.
inputSchema:
  type: object
  additionalProperties: false
  anyOf:
    - required: [args]
    - required: [input]
  properties:
    args:
      type: array
      description: Explicit CLI suffix arguments after scripts/run_actuarial_cli.py --json.
      items:
        type: string
    input:
      type: string
      description: Project-relative JSON/YAML input path consumed by actuarial_cli_hub.
    artifactRoot:
      type: string
      description: Optional artifact output directory.
    runId:
      type: string
      description: Optional stable run id.
outputSchema:
  type: object
  additionalProperties: true
  required: [ok, status]
  properties:
    ok:
      type: boolean
    status:
      type: string
      enum: [ok, error]
    tool_id:
      type: string
    run_id:
      type: string
    artifact_root:
      type: string
    artifacts:
      type: object
      additionalProperties: true
    error:
      type: [object, "null"]
interactionKinds:
  - approval
  - blocked
artifactKinds:
  - deterministic_result
  - diagnostics
  - explanation_markdown
  - aggregate_result
  - mortality_result
  - run_manifest
ui:
  mode: renderer
  openOnTrigger: false
  preferredRenderer: json
permissions:
  approvalRequired: true
  canUseNetwork: false
  canWriteDatabase: false
```

This preview manifest should be produced and validated inside `actuarial_cli_hub`. It should be implemented in `ai_interface` later, in a separate PR that either:

1. adds a specific `projectFallback` mapping for `moduleId: actuarial_cli_hub`, with `requiredPath: scripts/run_actuarial_cli.py`; or
2. generalizes `ai_interface` fallback resolution so manifest metadata can declare the required path without code-level special casing.

### 7.2 Compatibility Requirements for `actuarial_cli_hub`

To be compatible with the existing `ai_interface` safe CLI executor, `actuarial_cli_hub` must:

1. Provide a repo-local script entrypoint for sibling checkout execution:

```bash
python scripts/run_actuarial_cli.py --json ...
```

2. Also provide an installed-package module entrypoint for normal CLI users:

```bash
python -m actuarial_cli_hub --json ...
```

3. Keep both entrypoints behaviorally equivalent and covered by tests.
4. Avoid requiring shell features, pipes, or chained commands.
5. Accept argv-only configuration; do not require interactive prompts.
6. Support bounded output through artifact files instead of large stdout dumps.
7. Emit redaction-safe JSON envelopes; do not print secrets or absolute local env values unless necessary.
8. Work from project root as cwd when invoked through `scripts/run_actuarial_cli.py`.
9. Prefer `args: string[]` as the `ai_interface` input contract. Let `actuarial_cli_hub` consume structured JSON/YAML through `--input path`, because the current `ai_interface` CLI executor only maps a small set of structured fields automatically.
10. Keep command prefixes allowlist-friendly, e.g.:

```text
python scripts/run_actuarial_cli.py reserve chainladder
python scripts/run_actuarial_cli.py loss aggregate
python scripts/run_actuarial_cli.py registry validate
python scripts/run_actuarial_cli.py skills export
python -m actuarial_cli_hub reserve chainladder
python -m actuarial_cli_hub loss aggregate
```

### 7.3 Pipeline Compatibility Boundary

For v1, treat `actuarial_cli_hub` as **one executable skill** from the perspective of `ai_interface`. It can internally run multi-step actuarial workflows and emit a run manifest plus artifacts, but `ai_interface` should only be expected to render the stdout envelope and artifact files.

Native step-level `ai_interface` orchestration—where each actuarial step appears as an `ai_interface` DAG/pipeline step such as `chainladder-calc`, `narrative-draft`, or `report-export`—is a later integration enhancement. It requires a separate `ai_interface` PR to adapt or register those step manifests; it is not a zero-change property of placing pipeline YAML in `actuarial_cli_hub`.

---

## 8. MVP Scope

### MVP 0 — Contract/docs bootstrap

**Goal:** establish the repository as a serious, contract-first tool hub before runtime implementation.

**Files:**
- `README.md`
- `docs/architecture.md`
- `docs/wrapper-standard.md`
- `docs/ai-interface-integration.md`
- `registry/schemas/tool-manifest.schema.json`
- `registry/tools/chainladder-python.yaml`
- `registry/tools/aggregate.yaml`

**Acceptance criteria:**
- README explains product positioning, non-goals, and v1 architecture.
- Tool manifest schema validates the two seed manifests.
- `ai_interface` integration doc maps to the observed skill/CLI executor shape.
- No runtime claims are made before runtime exists.

### MVP 1 — Chainladder reserving CLI

**Goal:** first real executable vertical slice.

**Command:**

```bash
python -m actuarial_cli_hub reserve chainladder \
  --input examples/reserving/sample_triangle.csv \
  --output .tmp/runs/chainladder-demo/output/deterministic_result.json \
  --diagnostics-output .tmp/runs/chainladder-demo/output/diagnostics.json \
  --explain-output .tmp/runs/chainladder-demo/output/explanation.md \
  --json
```

**Files:**
- `pyproject.toml`
- `src/actuarial_cli_hub/cli.py`
- `src/actuarial_cli_hub/__main__.py`
- `src/actuarial_cli_hub/contracts/reserving.py`
- `src/actuarial_cli_hub/adapters/chainladder_adapter.py`
- `src/actuarial_cli_hub/commands/reserve.py`
- `examples/reserving/sample_triangle.csv`
- `examples/reserving/case_input.json`
- `tests/test_chainladder_cli.py`

**Acceptance criteria:**
- `python scripts/run_actuarial_cli.py --help` works from the repo root without requiring editable install.
- `python -m actuarial_cli_hub --help` works after `pip install -e '.[dev]'`.
- `python scripts/run_actuarial_cli.py reserve chainladder --help` and `python -m actuarial_cli_hub reserve chainladder --help` expose equivalent command behavior.
- Sample fixture run emits a JSON envelope with `ok: true`.
- Output artifact validates against `reserving-result.schema.json`.
- Invalid input emits `ok: false` JSON with stable error code.

### MVP 2 — Agent skill and `ai_interface` manifest export

**Goal:** make the tool discoverable by agents and easy for `ai_interface` to consume.

**Commands:**

```bash
python -m actuarial_cli_hub registry validate --json
python -m actuarial_cli_hub skills export --target hermes --output skills/hermes
python -m actuarial_cli_hub skills export --target ai_interface --output skills/ai_interface
```

**Files:**
- `src/actuarial_cli_hub/registry/loader.py`
- `src/actuarial_cli_hub/registry/validator.py`
- `src/actuarial_cli_hub/skills/generator.py`
- `skills/hermes/actuarial-reserving/SKILL.md`
- `skills/ai_interface/actuarial_cli_hub/skill.yaml`
- `tests/test_registry_contracts.py`
- `tests/test_skill_export.py`

**Acceptance criteria:**
- Registry validation passes in CI.
- Generated/checked-in Hermes skill includes exact CLI calls, input/output artifact semantics, and limitations.
- `skills/ai_interface/actuarial_cli_hub/skill.yaml` is compatible with the shape observed in `ai_interface` but is not automatically copied there.

### MVP 3 — Aggregate loss CLI

**Goal:** prove the hub can wrap non-table/DSL-like actuarial tooling.

**Command:**

```bash
python -m actuarial_cli_hub loss aggregate \
  --decl "agg MyLine 100 claims 1000 xs 0 sev lognorm 50 cv 1" \
  --output .tmp/runs/aggregate-demo/output/result.json \
  --explain-output .tmp/runs/aggregate-demo/output/explanation.md \
  --json
```

**Acceptance criteria:**
- Supports both inline `--decl` and YAML input.
- Emits structured result and limitations.
- Has golden fixture tests.

### MVP 4 — Mortality lookup spike

**Goal:** evaluate a cross-language adapter path without committing to heavy Julia/R install requirements for core users.

**Options:**
1. Native JuliaActuary adapter with optional extra and clear readiness checks.
2. Python-side static mortality fixture adapter for v1 demo, with documented future Julia path.

**Acceptance criteria:**
- `pip install actuarial_cli_hub` remains lightweight.
- Optional runtime dependencies are gated behind extras or external readiness checks.
- `ai_interface` readiness can report missing optional runtime without failing the whole hub.

### MVP 5 — Life/cash-flow modeling spike

**Goal:** decide whether `cashflower` or `lifelib` is the first life adapter.

**Decision criteria:**
- install friction;
- model fixture stability;
- artifact output clarity;
- IFRS 17 demonstration value;
- suitability for agent explanation and review.

---

## 9. Implementation PR Plan

### PR 1 — Docs and contracts bootstrap

**Scope:** no runtime yet.

**Files:**
- `README.md`
- `docs/architecture.md`
- `docs/wrapper-standard.md`
- `docs/ai-interface-integration.md`
- `docs/plans/2026-05-21-ai-interface-integration-roadmap.md`
- `registry/schemas/tool-manifest.schema.json`
- `registry/tools/chainladder-python.yaml`
- `registry/tools/aggregate.yaml`

**Validation:**

```bash
python -m json.tool registry/schemas/tool-manifest.schema.json >/dev/null
python - <<'PY'
import pathlib, yaml
for path in pathlib.Path('registry/tools').glob('*.yaml'):
    data = yaml.safe_load(path.read_text())
    assert data['id']
    assert data['runtime']['kind'] == 'cli'
print('manifest smoke ok')
PY
git diff --check
```

### PR 2 — Python package skeleton and executable entrypoint strategy

**Scope:** package structure, CLI help, and both execution entrypoints; no actuarial calculation yet. This PR must settle the compatibility-critical question of how a sibling checkout can be executed by `ai_interface` without assuming editable install.

**Files:**
- `pyproject.toml`
- `scripts/run_actuarial_cli.py`
- `src/actuarial_cli_hub/__init__.py`
- `src/actuarial_cli_hub/__main__.py`
- `src/actuarial_cli_hub/cli.py`
- `tests/test_cli_help.py`
- `tests/test_entrypoint_equivalence.py`

**Validation:**

```bash
python scripts/run_actuarial_cli.py --help
python scripts/run_actuarial_cli.py registry validate --json
python -m pip install -e '.[dev]'
python -m actuarial_cli_hub --help
python -m actuarial_cli_hub registry validate --json
pytest -q
```

### PR 3 — Chainladder reserving vertical slice

**Scope:** first real tool.

**Files:** see MVP 1.

**Validation:**

```bash
python scripts/run_actuarial_cli.py reserve chainladder --help
python scripts/run_actuarial_cli.py reserve chainladder \
  --input examples/reserving/sample_triangle.csv \
  --output .tmp/test-chainladder/deterministic_result.json \
  --diagnostics-output .tmp/test-chainladder/diagnostics.json \
  --explain-output .tmp/test-chainladder/explanation.md \
  --json
python -m actuarial_cli_hub reserve chainladder --help
pytest tests/test_chainladder_cli.py -q
pytest -q
```

### PR 4 — Skill exports and ai_interface compatibility preview

**Scope:** generated/checked-in skills, preview manifests, and compatibility tests. This PR still does not modify `ai_interface`; it proves that the handoff artifact uses the observed `ai_interface` manifest shape and safe CLI constraints.

**Files:** see MVP 2, plus:
- `tests/test_ai_interface_manifest_preview.py`
- `examples/ai_interface/agent-run-input.json`

**Validation:**

```bash
python scripts/run_actuarial_cli.py registry validate --json
python scripts/run_actuarial_cli.py skills export --target hermes --output .tmp/skills/hermes
python scripts/run_actuarial_cli.py skills export --target ai_interface --output .tmp/skills/ai_interface
pytest tests/test_skill_export.py tests/test_ai_interface_manifest_preview.py -q
```

**Compatibility assertions:**
- Manifest includes `inputSchema`, `outputSchema`, `interactionKinds`, `artifactKinds`, `ui`, and `permissions`.
- `execution.command` starts with `python scripts/run_actuarial_cli.py`.
- `execution.allowedCommands` contains the same safe prefix.
- The manifest states that a later `ai_interface` PR is required for project fallback unless `ACTUARIAL_CLI_HUB_PROJECT_PATH` is configured explicitly.

### PR 5 — Aggregate loss vertical slice

**Scope:** second runtime adapter.

**Validation:**

```bash
python -m actuarial_cli_hub loss aggregate --help
python -m actuarial_cli_hub loss aggregate \
  --decl "agg MyLine 100 claims 1000 xs 0 sev lognorm 50 cv 1" \
  --output .tmp/test-aggregate/result.json \
  --explain-output .tmp/test-aggregate/explanation.md \
  --json
pytest tests/test_aggregate_cli.py -q
pytest -q
```

### PR 6 — Optional ai_interface integration handoff hardening

**Scope:** optional documentation hardening if PR 4 does not already contain enough handoff material. Still do not edit `ai_interface` in this PR.

**Files:**
- `docs/ai-interface-integration.md`
- `skills/ai_interface/actuarial_cli_hub/skill.yaml`
- `examples/ai_interface/agent-run-input.json`

**Validation:**
- Check manifest shape against the observed `ai_interface` contract.
- Confirm command prefix is allowlist-friendly.
- Confirm default sibling path, env names, and required future `ai_interface` fallback mapping are documented.
- Confirm the doc distinguishes single-skill artifact rendering from future step-level DAG/pipeline integration.

A later, separate `ai_interface` PR can copy/adapt the manifest and add either a module-specific `projectFallback` mapping or a generalized manifest-driven fallback mechanism.

---

## 10. Validation and CI Strategy

### 10.1 Local checks for every PR

```bash
python scripts/run_actuarial_cli.py --help
python scripts/run_actuarial_cli.py registry validate --json
python -m pip install -e '.[dev]'
pytest -q
python -m actuarial_cli_hub --help
python -m actuarial_cli_hub registry validate --json
git diff --check
```

### 10.2 Contract checks

- Every registry manifest validates against `tool-manifest.schema.json`.
- Every command has `--help` coverage.
- Every runtime command has at least one golden fixture.
- Every error path returns JSON with `ok: false` and a stable `error.code`.
- No command requires interactivity.
- No test depends on external API keys.

### 10.3 ai_interface compatibility checks

Until the actual `ai_interface` PR is opened, compatibility checks remain local to `actuarial_cli_hub`:

- Generated skill manifest includes required `skillId`, `moduleId`, `project`, `execution`, `inputSchema`, `outputSchema`, `artifactKinds`, `ui`, and `permissions` fields.
- `execution.command` starts with an allowlisted, shell-free prefix.
- Artifact outputs are relative paths inside a run root.
- Output envelope is small enough for `maxOutputBytes`; large payloads are artifact files.

---

## 11. Risk Register

| Risk | Impact | Mitigation |
|---|---|---|
| Scope creep into "convert every actuarial repo" | High | Start contract-first; support two tools before automation. |
| Heavy R/Julia installs break core UX | Medium | Keep core Python-only; optional extras/readiness checks for R/Julia. |
| Upstream APIs change | Medium | Pin dependency ranges and use golden contract tests. |
| `ai_interface` manifest contract changes | Medium | Keep generated manifest isolated and validate against the live repo before integration PR. |
| `src/` layout plus `python -m` does not work from an uninstalled sibling checkout | High | Provide `scripts/run_actuarial_cli.py` that bootstraps `src/`; keep `python -m` for installed-package use and test both. |
| `ai_interface` sibling fallback is currently code-mapped, not fully manifest-driven | High | Treat the `ai_interface` manifest as a preview artifact; require a later `ai_interface` PR for projectFallback mapping or generalized fallback. |
| `ai_interface` CLI input mapping is intentionally limited | Medium | Use explicit `args: string[]` and file inputs (`--input path`) as the v1 contract instead of expecting arbitrary structured argument mapping. |
| Stdout envelope or artifact path conventions drift | Medium | Freeze envelope v1 in PR 1/2 and add golden tests for success and error outputs. |
| Agent overclaims actuarial correctness | High | Skills and output explanations must include limitations and actuarial review boundary. |
| Large stdout breaks safe executor | Medium | Write large outputs to artifacts and keep stdout envelope small. |
| Regulatory-production confusion | High | README and skills must explicitly say methodology validation / research / teaching, not regulatory reporting. |

---

## 12. Open Decisions

1. **First life adapter:** `cashflower` first for lower friction, or `lifelib` first for IFRS 17 reference value?
   - Recommendation: `cashflower` first, `lifelib` spike second.
2. **Mortality adapter:** direct JuliaActuary dependency or Python fixture bridge first?
   - Recommendation: spike both; keep core install lightweight.
3. **Manifest ownership:** should `skills/ai_interface/actuarial_cli_hub/skill.yaml` be generated from registry or manually maintained?
   - Recommendation: check in generated output initially, then add generator once schema stabilizes.
4. **CLI framework:** Typer vs argparse.
   - Recommendation: Typer for ergonomic subcommands and help; argparse if minimizing dependencies becomes more important.
5. **Schema source of truth:** Pydantic models exported to JSON Schema vs hand-written JSON Schema.
   - Recommendation: Pydantic source of truth for runtime contracts; hand-written schema only for registry manifest if simpler.

---

## 13. Recommended Next Action

Implement **PR 1: Docs and contracts bootstrap** in `actuarial_cli_hub`:

1. Update README with positioning and non-goals.
2. Add architecture and wrapper-standard docs.
3. Add this plan under `docs/plans/`.
4. Add `tool-manifest.schema.json`.
5. Add seed manifests for `chainladder-python` and `aggregate`.
6. Run manifest smoke validation and `git diff --check`.
7. Run Codex review gate before commit/push/PR.

Only after PR 1 is merged should implementation move to the CLI package skeleton and runtime commands.
