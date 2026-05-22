---
name: cashflow-cashflower
description: Use `actuary cashflow cashflower` from actuarial_cli_hub for Cashflower Cash-flow Runner workflows.
version: 0.1.0
metadata:
  source_tool_id: actuarial.cashflow.cashflower
  runtime_availability: implemented
  use_cases:
    - Cash-flow model demo runs
    - Agent-readable model output artifacts
  limitations:
    - Model code is user supplied and must be reviewed
    - Wrapper runs user supplied model.py files in an isolated temporary directory but does not sandbox arbitrary Python code
---

# Cashflower Cash-flow Runner

Use this skill when an agent needs the `actuarial.cashflow.cashflower` tool from `actuarial_cli_hub`.

## Command

```bash
actuary cashflow cashflower --help
```

## Artifact Contract

- `deterministic_result`
- `diagnostics`

## Safety Notes

- Treat outputs as actuarial analysis aids, not signed actuarial opinions.
- Keep upstream repositories and downstream consumers read-only unless a separate task explicitly scopes changes there.
