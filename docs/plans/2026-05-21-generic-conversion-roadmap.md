# actuarial_cli_hub Generic Conversion Roadmap

> **For Hermes/Codex implementers:** this is an `actuarial_cli_hub` implementation plan. Do not modify `ferryhe/ai_interface` in these PRs. Treat every external repo—including `ai_interface` and upstream actuarial OSS—as a read-only integration or wrapping target unless a later task explicitly scopes changes there.

**Date:** 2026-05-21

**Repos:**
- Runtime/tooling repo to modify: `https://github.com/ferryhe/actuarial_cli_hub`
- Read-only downstream consumer inspected for compatibility: `https://github.com/ferryhe/ai_interface`
- Read-only upstream actuarial OSS targets: `chainladder-python`, `aggregate`, `cashflower`, `lifelib/modelx`, JuliaActuary/MortalityTables.jl, `lifecontingencies`, `insurancerating`, `FASLR`, Loss Data Analytics materials, and actuarial OSS catalog repos

---

## 1. Executive Summary

`actuarial_cli_hub` should become a **generic conversion hub** for actuarial open-source software: it turns heterogeneous Python/R/Julia/notebook/reference repositories into stable, agent-native CLI tools with manifests, schemas, fixtures, skills, and artifact contracts. The plan is for `actuarial_cli_hub` only. It should not modify `ai_interface`, and it should not fork or rewrite upstream actuarial libraries unless a tiny compatibility shim is unavoidable and isolated.

The clean architecture is:

```text
actuarial_cli_hub
  -> owns the `actuary` CLI, registry, schemas, fixtures, adapter SDK, skills, and artifacts
  -> classifies upstream actuarial OSS by domain and wrapability
  -> invokes each upstream package/repo behind a stable CLI/file contract
  -> exports optional skill/manifest packs for agents and downstream UIs

upstream actuarial OSS, read-only by default
  -> chainladder-python, aggregate, cashflower, lifelib/modelx, JuliaActuary, R actuarial packages, FASLR, books/catalogs

downstream consumers, read-only by default
  -> humans on CLI, Hermes/Codex/Claude agents, ai_interface, CI jobs, notebooks, future HTTP/MCP wrappers
```

The core product is not an `ai_interface` adapter. The core product is a reusable conversion framework: **Registry → Domain Schema → Adapter → CLI Command → Artifact Contract → Golden Fixture → Skill Pack**. `ai_interface` is only one downstream consumer used to sanity-check that the contracts are agent-friendly.

---

## 2. Read-only Consumer Compatibility Notes

`ai_interface` was inspected only to ensure the generic CLI contracts are downstream-consumer friendly. These findings do not change the scope: all implementation work remains inside `actuarial_cli_hub`. Relevant observed facts:

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

**Implication:** design `actuarial_cli_hub` as a standalone CLI/file-artifact product first. Downstream UIs such as `ai_interface` can consume it later, but no `ai_interface` changes are part of this plan. The `ai_interface` notes only reinforce that shell-free commands, bounded stdout, explicit artifacts, and complete manifests are the right generic contract.

---

## 3. Product Definition

### 3.1 One-line Positioning

**`actuarial_cli_hub` converts actuarial open-source software into agent-native CLI tools through stable registries, schemas, adapters, examples, artifacts, and skills.**

### 3.2 Non-goals for v1

- Do not rewrite upstream actuarial libraries.
- Do not embed `ai_interface` code or depend on its TypeScript internals; downstream integration manifests are preview exports only.
- Do not expose a long-running HTTP service in v1.
- Do not expose MCP in v1.
- Do not claim regulatory-production readiness.
- Do not promise automatic wrapper generation for every actuarial repo before the manual conversion factory proves useful on representative Python, DSL, R, Julia, and reference-material targets.

### 3.3 Target Users

1. **Actuarial practitioners** who want reproducible command-line workflows for reserving, aggregate loss, mortality, cash-flow, or IFRS 17 experiments.
2. **AI agents** that need predictable, bounded, artifact-based tool calls.
3. **AI agents and downstream UIs** that need skills and tool manifests they can inspect, execute, and display.
4. **Open-source actuarial contributors** who want a standard way to make their packages consumable by agents.
5. **Educators/researchers** who want repeatable demos from books, catalogs, and reference implementations even when those sources are not runtime libraries.

---

## 4. Architecture

### 4.1 Runtime Layers

```text
┌───────────────────────────────────────────────────────────┐
│ actuarial_cli_hub                                          │
│ - `actuary` CLI                                             │
│ - registry/tool manifests                                  │
│ - domain schemas and JSON/Pydantic contracts               │
│ - adapter SDK + runtime bridges                            │
│ - fixtures/golden outputs                                  │
│ - generated agent skills and portable tool cards           │
└───────────────────────────┬───────────────────────────────┘
                            │ stable CLI/file contracts
                            ▼
┌───────────────────────────────────────────────────────────┐
│ Upstream actuarial OSS, read-only by default               │
│ - casact/chainladder-python                                │
│ - mynl/aggregate                                           │
│ - acturtle/cashflower                                      │
│ - lifelib-dev/lifelib + fumitoh/modelx                     │
│ - JuliaActuary packages / MortalityTables.jl               │
│ - R packages such as lifecontingencies / insurancerating   │
│ - FASLR, Loss Data Analytics, actuarial-foss catalogs      │
└───────────────────────────┬───────────────────────────────┘
                            │ exported manifests/artifacts
                            ▼
┌───────────────────────────────────────────────────────────┐
│ Downstream consumers, read-only by default                 │
│ - humans on terminal                                       │
│ - Hermes/Codex/Claude/Cursor agents                        │
│ - ai_interface or other UIs                                │
│ - CI jobs, notebooks, future HTTP/MCP wrappers             │
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
  -> agent skill / downstream tool manifest
```

Do not duplicate business logic between CLI, future HTTP, and future MCP adapters. The stable core should be the pure adapter function plus Pydantic contracts.

### 4.3 Generic Conversion Factory

Every previously mentioned actuarial project should move through the same conversion pipeline. The pipeline is intentionally repetitive so new projects can be added without inventing a new pattern each time.

```text
1. Discover
   -> read README/docs/examples/tests; identify public CLI/API/notebook entrypoints and license/runtime constraints
2. Classify
   -> assign domain, runtime class, complexity, dependency weight, and agent use cases
3. Contract
   -> define canonical input schema, output schema, error envelope, artifact names, and limitations
4. Fixture
   -> add the smallest reproducible example input plus expected/golden output
5. Adapter
   -> implement a thin wrapper around the upstream public API/CLI, not private internals
6. CLI
   -> expose a stable `actuary <domain> <tool>` command with `--input`, `--output`, `--json`, and artifact flags
7. Validate
   -> run help tests, manifest validation, fixture tests, invalid-input tests, and optional runtime readiness checks
8. Skill
   -> add agent instructions explaining when to use the command, what the result means, and where human actuarial review is required
9. Promote
   -> move status from `cataloged` -> `manifested` -> `experimental` -> `stable` only after fixtures and tests pass
```

Recommended status model:

| Status | Meaning | Required evidence |
|---|---|---|
| `cataloged` | Known project listed in registry only | URL, domain, language, license/install notes |
| `manifested` | Machine-readable manifest exists | Manifest validates; no runtime wrapper required yet |
| `fixture-ready` | Minimal example inputs/expected artifacts exist | Example data committed; schema draft exists |
| `experimental` | CLI command runs locally | Help test, success fixture, error envelope test |
| `stable` | Safe default for agents | Golden tests, docs, limitations, version pin/readiness checks |
| `external-reference` | Not a runtime tool; useful as knowledge/catalog source | Search/index/summarization contract instead of execution adapter |

### 4.4 Conversion Taxonomy for the Actuarial OSS Map

The goal is to convert the whole previously discussed ecosystem, but not all entries become executable CLI wrappers. Some become runtime tools, some become optional cross-runtime adapters, and some become curated knowledge/reference packs.

| Target | Domain | Runtime class | First conversion form | Target CLI shape | Priority |
|---|---|---|---|---|---|
| `chainladder-python` | P&C reserving | Python library | full wrapper | `actuary reserve chainladder` | P0 |
| `aggregate` | aggregate loss / risk | Python package + declarative DSL | full wrapper | `actuary loss aggregate` | P0 |
| `cashflower` | life/cash-flow modeling | Python package | model-run wrapper | `actuary cashflow cashflower` | P1 |
| `lifelib` + `modelx` | life/IFRS 17 modeling | Python model library | project/template runner | `actuary life lifelib` | P1/P2 |
| JuliaActuary / `MortalityTables.jl` | mortality / life contingencies | Julia package | optional runtime adapter | `actuary mortality table` | P2 |
| R `lifecontingencies` | life contingencies | R package | optional Rscript adapter | `actuary lifecontingencies r` | P2 |
| R `insurancerating` | pricing / GLM rating | R package | optional Rscript adapter | `actuary pricing insurancerating` | P2 |
| `FASLR` | reserving GUI/workbench | Python GUI/application | catalog + selective CLI extraction if public API is stable | `actuary reserve faslr` only after spike | P3 |
| Loss Data Analytics materials | education/reference/data | book/data/notebooks | reference/data pack, not calculation wrapper | `actuary reference lda` | P3 |
| `actuarial-foss` / curated OSS lists | catalog/discovery | metadata repo | registry seed/importer | `actuary registry import-catalog` | P0/P1 |

### 4.5 File/Artifact Contract

The CLI should always support explicit artifact paths:

```bash
actuary reserve chainladder \
  --input examples/reserving/sample_triangle.csv \
  --output .tmp/actuarial-cli-runs/demo/output/deterministic_result.json \
  --diagnostics-output .tmp/actuarial-cli-runs/demo/output/diagnostics.json \
  --explain-output .tmp/actuarial-cli-runs/demo/output/explanation.md \
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
    "explanation_markdown": "output/explanation.md"
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
    conversion-factory.md
    adapter-catalog.md
    agent-skill-standard.md
    plans/
      2026-05-21-generic-conversion-roadmap.md
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

## 7. Optional Downstream Export Contract

### 7.1 Example Downstream Skill Shape

The core CLI must not depend on any downstream UI. As a compatibility exercise, `actuarial_cli_hub` may export a preview skill manifest for `ai_interface` because that consumer has a useful safe-CLI model. **Important constraint:** in the current `ai_interface` implementation, sibling project fallback is not fully manifest-driven. `project.defaultSiblingPath` is metadata, but executable fallback currently becomes reliable only when `ai_interface` maps a module to a `projectFallback.requiredPath` in code. Therefore, the manifest below is a **preview/handoff export**, not a claim that copying it into `ai_interface` will work without a later `ai_interface` PR.

The recommended generic execution model is still useful beyond `ai_interface`: use a repo-local script that can bootstrap `src/` layout imports from a sibling checkout, plus an installed-package entrypoint for normal CLI use.

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

### 7.2 Generic CLI Compatibility Requirements for `actuarial_cli_hub`

To be compatible with safe CLI executors used by agents, UIs, CI jobs, and notebooks, `actuarial_cli_hub` must:

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
9. Prefer `args: string[]` as the lowest-common-denominator downstream input contract. Let `actuarial_cli_hub` consume structured JSON/YAML through `--input path`, because many safe CLI executors only map a small set of structured fields automatically.
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

For v1, treat `actuarial_cli_hub` as **one executable CLI product** from the perspective of any downstream consumer. It can internally run multi-step actuarial workflows and emit a run manifest plus artifacts, but external consumers should only need to parse the stdout envelope and read artifact files.

Native step-level orchestration in a downstream UI—where each actuarial step appears as a visible DAG/pipeline node such as `chainladder-calc`, `narrative-draft`, or `report-export`—is a later downstream integration enhancement. It is not a requirement for building the generic CLI hub.

---

## 8. Product Milestones: Generic CLI First, Then Full Ecosystem Conversion

The milestones below are intentionally `actuarial_cli_hub`-only. They create a reusable conversion machine first, then feed every previously discussed actuarial OSS target through it.

### Milestone 0 — Contract/docs bootstrap

**Goal:** establish `actuarial_cli_hub` as a generic, contract-first conversion hub before runtime implementation.

**Files:**
- `README.md`
- `docs/architecture.md`
- `docs/wrapper-standard.md`
- `docs/conversion-factory.md`
- `docs/adapter-catalog.md`
- `docs/plans/2026-05-21-generic-conversion-roadmap.md`
- `registry/schemas/tool-manifest.schema.json`
- `registry/schemas/domain.schema.json`
- `registry/schemas/envelope.schema.json`
- `registry/tools/*.yaml` for all P0/P1/P2/P3 targets

**Acceptance criteria:**
- README says this is a generic actuarial CLI hub, not an `ai_interface` subproject.
- All previously discussed projects are listed in registry with status and conversion class.
- No runtime claims are made before runtime exists.
- Manifest validation can run without installing actuarial runtimes.

### Milestone 1 — CLI core and adapter SDK

**Goal:** build the reusable CLI/adapter skeleton that every conversion target will share.

**Commands:**

```bash
python scripts/run_actuarial_cli.py --help
python scripts/run_actuarial_cli.py registry list --json
python scripts/run_actuarial_cli.py registry validate --json
python scripts/run_actuarial_cli.py doctor --json
```

**Core components:**
- `src/actuarial_cli_hub/cli.py`
- `src/actuarial_cli_hub/registry/loader.py`
- `src/actuarial_cli_hub/registry/validator.py`
- `src/actuarial_cli_hub/runtime/envelope.py`
- `src/actuarial_cli_hub/runtime/artifacts.py`
- `src/actuarial_cli_hub/adapters/base.py`
- `scripts/run_actuarial_cli.py`

**Acceptance criteria:**
- Repo-local script works from a bare sibling checkout.
- Installed package entrypoint also works.
- All commands are shell-free and stdout-bounded.
- Success/error envelope v1 is frozen with tests.

### Milestone 2 — P0 Python runtime wrappers: reserving + aggregate loss

**Goal:** prove the conversion factory on two high-value, low-friction Python tools with different input styles.

**Targets:**
1. `chainladder-python` — table/file-driven reserving.
2. `aggregate` — declarative aggregate loss DSL.

**Commands:**

```bash
python scripts/run_actuarial_cli.py reserve chainladder \
  --input examples/reserving/sample_triangle.csv \
  --output .tmp/actuarial-cli-runs/chainladder-demo/output/deterministic_result.json \
  --diagnostics-output .tmp/actuarial-cli-runs/chainladder-demo/output/diagnostics.json \
  --explain-output .tmp/actuarial-cli-runs/chainladder-demo/output/explanation.md \
  --json

python scripts/run_actuarial_cli.py loss aggregate \
  --decl "agg MyLine 100 claims 1000 xs 0 sev lognorm 50 cv 1" \
  --output .tmp/actuarial-cli-runs/aggregate-demo/output/result.json \
  --explain-output .tmp/actuarial-cli-runs/aggregate-demo/output/explanation.md \
  --json
```

**Acceptance criteria:**
- Each wrapper has manifest, schema, fixture, CLI command, error envelope, and skill docs.
- Each wrapper has one success golden test and one invalid-input test.
- Optional package dependencies are pinned or bounded.

### Milestone 3 — P1 life/cash-flow Python wrappers

**Goal:** extend the same wrapper factory to actuarial model-running workflows, not just single calculation functions.

**Targets:**
1. `cashflower` — lower-friction cash-flow/model runner.
2. `lifelib` + `modelx` — template/model runner for life/IFRS 17 style examples.

**Commands:**

```bash
python scripts/run_actuarial_cli.py cashflow cashflower   --model examples/cashflower/simple_model.py   --assumptions examples/cashflower/assumptions.yaml   --output .tmp/actuarial-cli-runs/cashflower-demo/output/cashflows.json   --json

python scripts/run_actuarial_cli.py life lifelib   --template basiclife   --scenario examples/lifelib/scenario.yaml   --output .tmp/actuarial-cli-runs/lifelib-demo/output/result.json   --json
```

**Acceptance criteria:**
- The hub treats model directories as inputs and output artifacts as contracts.
- `doctor --json` reports missing optional model dependencies clearly.
- The wrappers do not copy large upstream model code into this repo.

### Milestone 4 — P2 cross-runtime adapters: Julia and R

**Goal:** support non-Python actuarial tools without making the core install heavy.

**Targets:**
1. JuliaActuary / `MortalityTables.jl` — mortality table lookup and simple life-contingency calculations.
2. R `lifecontingencies` — life-contingency examples through `Rscript`.
3. R `insurancerating` — pricing/rating examples through `Rscript`.

**Commands:**

```bash
python scripts/run_actuarial_cli.py mortality table   --source julia-actuary   --table examples/mortality/table_request.yaml   --output .tmp/actuarial-cli-runs/mortality-demo/output/result.json   --json

python scripts/run_actuarial_cli.py lifecontingencies r   --input examples/lifecontingencies/case.yaml   --output .tmp/actuarial-cli-runs/lifecontingencies-demo/output/result.json   --json

python scripts/run_actuarial_cli.py pricing insurancerating   --input examples/insurancerating/glm_case.yaml   --output .tmp/actuarial-cli-runs/insurancerating-demo/output/result.json   --json
```

**Acceptance criteria:**
- Core `pip install` still works without Julia/R.
- Optional runtimes use `doctor` readiness checks.
- Tests skip gracefully when Julia/R are absent, but schema/manifest tests always run.
- Runtime adapters communicate through JSON files, not fragile stdout parsing.

### Milestone 5 — P3 applications and reference sources

**Goal:** convert non-library projects into useful registry/reference assets without forcing them into executable wrappers prematurely.

**Targets:**
1. `FASLR` — catalog first; wrapper only if a stable public calculation API/CLI exists.
2. Loss Data Analytics materials — reference/data pack.
3. `actuarial-foss` / curated OSS lists — registry importer and catalog seed.

**Commands:**

```bash
python scripts/run_actuarial_cli.py registry import-catalog   --source examples/catalogs/actuarial-foss.yaml   --output registry/generated/catalog.json   --json

python scripts/run_actuarial_cli.py reference lda search \
  --query "collective risk model aggregate loss" \
  --output .tmp/actuarial-cli-runs/lda-search/output/results.json \
  --json
```

**Acceptance criteria:**
- Reference sources are explicitly marked `external-reference`, not executable tools.
- The registry can import catalog entries without runtime dependencies.
- Agent skills explain when a reference source is appropriate versus when a calculation wrapper is required.

### Milestone 6 — Skill packs and downstream-consumer exports

**Goal:** produce portable instructions and manifests for agents and UIs without changing those downstream repos.

**Targets:**
- Hermes skill packs.
- Generic agent tool cards.
- Optional `ai_interface` preview manifest under `skills/ai_interface/`.

**Acceptance criteria:**
- Skills are generated from registry metadata where possible.
- Every executable command has a matching skill section with limitations.
- `ai_interface` preview is documented as an export artifact only; no `ai_interface` code is touched.

---

## 9. Implementation PR Plan

### PR 1 — Generic docs, registry taxonomy, and full catalog seed

**Scope:** no runtime yet. This PR should make the plan clearly about `actuarial_cli_hub` as a generic conversion hub.

**Files:**
- `README.md`
- `docs/architecture.md`
- `docs/wrapper-standard.md`
- `docs/conversion-factory.md`
- `docs/adapter-catalog.md`
- `docs/plans/2026-05-21-generic-conversion-roadmap.md`
- `registry/schemas/tool-manifest.schema.json`
- `registry/tools/chainladder-python.yaml`
- `registry/tools/aggregate.yaml`
- `registry/tools/cashflower.yaml`
- `registry/tools/lifelib.yaml`
- `registry/tools/modelx.yaml`
- `registry/tools/mortalitytables-jl.yaml`
- `registry/tools/lifecontingencies-r.yaml`
- `registry/tools/insurancerating-r.yaml`
- `registry/tools/faslr.yaml`
- `registry/tools/loss-data-analytics.yaml`
- `registry/tools/actuarial-foss.yaml`

**Validation:**

```bash
python -m json.tool registry/schemas/tool-manifest.schema.json >/dev/null
python - <<'PY'
import pathlib, yaml
paths = sorted(pathlib.Path('registry/tools').glob('*.yaml'))
assert len(paths) >= 10, paths
for path in paths:
    data = yaml.safe_load(path.read_text())
    assert data['id']
    assert data['status'] in {'cataloged','manifested','fixture-ready','experimental','stable','external-reference'}
    assert data['conversion']['class'] in {'python-library','python-dsl','python-model-runner','julia-adapter','r-adapter','application-spike','reference-pack','catalog-importer'}
print('catalog smoke ok')
PY
git diff --check
```

### PR 2 — CLI core, registry validator, artifact/envelope runtime

**Scope:** package structure and generic runtime only; no actuarial calculation yet.

**Files:**
- `pyproject.toml`
- `scripts/run_actuarial_cli.py`
- `src/actuarial_cli_hub/__init__.py`
- `src/actuarial_cli_hub/__main__.py`
- `src/actuarial_cli_hub/cli.py`
- `src/actuarial_cli_hub/runtime/envelope.py`
- `src/actuarial_cli_hub/runtime/artifacts.py`
- `src/actuarial_cli_hub/adapters/base.py`
- `src/actuarial_cli_hub/registry/loader.py`
- `src/actuarial_cli_hub/registry/validator.py`
- `tests/test_cli_help.py`
- `tests/test_entrypoint_equivalence.py`
- `tests/test_envelope_contract.py`
- `tests/test_registry_contracts.py`

**Validation:**

```bash
python scripts/run_actuarial_cli.py --help
python scripts/run_actuarial_cli.py registry list --json
python scripts/run_actuarial_cli.py registry validate --json
python scripts/run_actuarial_cli.py doctor --json
python -m pip install -e '.[dev]'
python -m actuarial_cli_hub --help
pytest -q
```

### PR 3 — P0 wrapper: `chainladder-python`

**Scope:** first runtime wrapper and first reserving schema.

**Validation:**

```bash
python scripts/run_actuarial_cli.py reserve chainladder --help
python scripts/run_actuarial_cli.py reserve chainladder \
  --input examples/reserving/sample_triangle.csv \
  --output .tmp/test-chainladder/deterministic_result.json \
  --diagnostics-output .tmp/test-chainladder/diagnostics.json \
  --explain-output .tmp/test-chainladder/explanation.md \
  --json
pytest tests/test_chainladder_cli.py tests/test_reserving_contracts.py -q
pytest -q
```

### PR 4 — P0 wrapper: `aggregate`

**Scope:** second runtime wrapper; proves DSL-style tools fit the same hub.

**Validation:**

```bash
python scripts/run_actuarial_cli.py loss aggregate --help
python scripts/run_actuarial_cli.py loss aggregate \
  --decl "agg MyLine 100 claims 1000 xs 0 sev lognorm 50 cv 1" \
  --output .tmp/test-aggregate/result.json \
  --explain-output .tmp/test-aggregate/explanation.md \
  --json
pytest tests/test_aggregate_cli.py tests/test_aggregate_contracts.py -q
pytest -q
```

### PR 5 — Generic skill generation and portable tool cards

**Scope:** convert registry metadata into agent-facing instructions. Do not modify downstream repos.

**Files:**
- `src/actuarial_cli_hub/skills/generator.py`
- `skills/hermes/actuarial-reserving/SKILL.md`
- `skills/hermes/actuarial-aggregate-loss/SKILL.md`
- `skills/generic/*.yaml`
- `skills/ai_interface/actuarial_cli_hub/skill.yaml` as preview export only
- `tests/test_skill_export.py`
- `tests/test_downstream_manifest_preview.py`

**Validation:**

```bash
python scripts/run_actuarial_cli.py skills export --target hermes --output .tmp/skills/hermes
python scripts/run_actuarial_cli.py skills export --target generic --output .tmp/skills/generic
python scripts/run_actuarial_cli.py skills export --target ai_interface --output .tmp/skills/ai_interface
pytest tests/test_skill_export.py tests/test_downstream_manifest_preview.py -q
```

### PR 6 — P1 wrapper: `cashflower`

**Scope:** first cash-flow/model-runner wrapper.

**Validation:**

```bash
python scripts/run_actuarial_cli.py cashflow cashflower --help
python scripts/run_actuarial_cli.py cashflow cashflower \
  --model examples/cashflower/simple_model.py \
  --assumptions examples/cashflower/assumptions.yaml \
  --output .tmp/test-cashflower/cashflows.json \
  --json
pytest tests/test_cashflower_cli.py -q
```

### PR 7 — P1/P2 wrapper: `lifelib` + `modelx`

**Scope:** model/template runner spike with clear optional dependency boundaries.

**Validation:**

```bash
python scripts/run_actuarial_cli.py life lifelib --help
python scripts/run_actuarial_cli.py doctor --runtime lifelib --json
pytest tests/test_lifelib_manifest.py tests/test_lifelib_cli.py -q
```

### PR 8 — P2 cross-runtime runtime manager

**Scope:** introduce Julia/R readiness checks and JSON bridge helpers before adding specific R/Julia wrappers.

**Files:**
- `src/actuarial_cli_hub/runtimes/julia.py`
- `src/actuarial_cli_hub/runtimes/r.py`
- `src/actuarial_cli_hub/adapters/subprocess_json.py`
- `tests/test_optional_runtime_doctor.py`
- `tests/test_subprocess_json_contract.py`

**Validation:**

```bash
python scripts/run_actuarial_cli.py doctor --runtime julia --json || true
python scripts/run_actuarial_cli.py doctor --runtime r --json || true
pytest tests/test_optional_runtime_doctor.py tests/test_subprocess_json_contract.py -q
```

### PR 9 — P2 wrappers: mortality + life contingencies + pricing

**Scope:** add optional wrappers for JuliaActuary/MortalityTables.jl, R `lifecontingencies`, and R `insurancerating`.

**Validation:**

```bash
python scripts/run_actuarial_cli.py mortality table --help
python scripts/run_actuarial_cli.py lifecontingencies r --help
python scripts/run_actuarial_cli.py pricing insurancerating --help
pytest tests/test_mortality_manifest.py tests/test_r_adapter_manifests.py -q
# Runtime integration tests may skip if Julia/R are absent.
pytest tests/integration_optional -q
```

### PR 10 — P3 catalog/reference adapters: FASLR, Loss Data Analytics, actuarial-foss

**Scope:** handle projects that are not clean runtime libraries.

**Validation:**

```bash
python scripts/run_actuarial_cli.py registry import-catalog --help
python scripts/run_actuarial_cli.py reference lda search --help
python scripts/run_actuarial_cli.py registry validate --json
pytest tests/test_reference_packs.py tests/test_catalog_importer.py -q
```

### PR 11 — Release hardening and conversion playbook

**Scope:** make it easy to add the next actuarial OSS repo after the initial map is covered.

**Files:**
- `docs/add-a-wrapper.md`
- `templates/adapter/`
- `templates/registry/tool.yaml`
- `templates/tests/test_tool_cli.py`
- `docs/release-checklist.md`

**Validation:**

```bash
python scripts/run_actuarial_cli.py registry validate --json
pytest -q
python scripts/run_actuarial_cli.py doctor --json
git diff --check
```

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

### 10.3 Downstream-consumer compatibility checks

Downstream compatibility checks remain local to `actuarial_cli_hub`. They ensure the generic CLI is easy for agents, UIs, notebooks, and CI jobs to consume without requiring changes in those downstream repos:

- Generated skill/tool manifests include required identity, project/runtime metadata, input/output schemas, artifact kinds, UI hints, and permissions/limitations fields.
- `execution.command` examples start with an allowlisted, shell-free prefix.
- Artifact outputs are relative paths inside a run root.
- Output envelope is small enough for `maxOutputBytes`; large payloads are artifact files.
- Optional downstream manifests, including `skills/ai_interface/`, are preview exports only and are not treated as completed downstream integration.

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

1. **CLI framework:** Typer vs argparse.
   - Recommendation: Typer for ergonomic subcommands and help; argparse if minimizing dependencies becomes more important.
2. **Schema source of truth:** Pydantic models exported to JSON Schema vs hand-written JSON Schema.
   - Recommendation: Pydantic source of truth for runtime contracts; hand-written schema only for registry manifest if simpler.
3. **R/Julia dependency policy:** optional extras vs external runtime detection only.
   - Recommendation: keep core Python-only; use `doctor` and runtime-specific extras/scripts for optional integrations.
4. **Reference-pack storage:** commit small curated fixtures vs download-on-demand for larger public materials.
   - Recommendation: commit only tiny fixtures and metadata; document download steps for larger materials.
5. **Wrapper promotion policy:** who decides when `experimental` becomes `stable`.
   - Recommendation: require golden tests, documented limitations, version pin/readiness checks, and at least one realistic example.

---

## 13. Recommended Next Action

Implement **PR 1: Generic docs, registry taxonomy, and full catalog seed** in `actuarial_cli_hub`:

1. Update README so the repo is positioned as a generic actuarial CLI conversion hub.
2. Add architecture, wrapper-standard, conversion-factory, and adapter-catalog docs.
3. Keep this roadmap under `docs/plans/`.
4. Add `tool-manifest.schema.json`, domain schema, and envelope schema.
5. Add registry manifests for all previously mentioned targets: `chainladder-python`, `aggregate`, `cashflower`, `lifelib/modelx`, JuliaActuary/MortalityTables.jl, R `lifecontingencies`, R `insurancerating`, `FASLR`, Loss Data Analytics materials, and `actuarial-foss`/catalog sources.
6. Run manifest smoke validation and `git diff --check`.
7. Run Codex review gate before commit/push/PR.

Only after PR 1 is merged should implementation move to the generic CLI core and adapter SDK. Runtime wrappers should then follow the priority order: P0 `chainladder` + `aggregate`, P1 `cashflower` + `lifelib/modelx`, P2 Julia/R adapters, P3 application/reference/catalog adapters.
