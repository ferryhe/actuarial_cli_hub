# Architecture

`actuarial_cli_hub` is a standalone runtime/tooling layer for actuarial open-source projects. It exposes each supported upstream project through stable CLI and file contracts rather than by asking downstream agents or UIs to understand each upstream library directly.

## Responsibility boundary

```text
actuarial_cli_hub
  owns: CLI, registry, schemas, adapters, fixtures, artifacts, generated skills

upstream actuarial OSS
  owns: calculation libraries, model runners, packages, examples, reference materials
  default: read-only wrapping targets

downstream consumers
  owns: UI/orchestration/agent workflows
  default: read-only consumers of CLI envelopes and artifacts
```

The hub should not import downstream UI code. Optional exports such as `skills/ai_interface/` are handoff artifacts only.

## Runtime layers

1. Registry manifests describe tools, domains, upstreams, conversion class, runtime expectations, schemas, and limitations.
2. Domain schemas define canonical inputs and outputs that remain stable even when upstream APIs change.
3. Thin adapters call public upstream APIs or CLIs. They do not reimplement actuarial methods.
4. CLI commands accept argv and file inputs, write artifacts, and emit bounded JSON envelopes.
5. Skills and tool cards teach agents when to use a tool and when human actuarial review is required.

## Artifact contract

Canonical run roots should use `.tmp/actuarial-cli-runs/<run_id>/`. Result payloads live under `output/`, while stdout stays small and machine-readable. Common artifact ids are `deterministic_result`, `diagnostics`, `explanation_markdown`, `aggregate_result`, `mortality_result`, and `run_manifest`.

## Promotion rule

A manifest status is evidence-based. Do not mark a tool `experimental` until its command runs locally with tests. Do not mark it `stable` until golden fixtures, error envelopes, docs, limitations, and readiness checks are in place.
