---
name: actuarial-reserving
description: Use `actuary reserve chainladder` from actuarial_cli_hub for Chainladder Reserving workflows.
version: 0.1.0
metadata:
  source_tool_id: actuarial.reserve.chainladder
  runtime_availability: implemented
  use_cases:
    - P&C loss reserving methodology validation
    - triangle diagnostics
    - reserving demo or teaching workflow
  limitations:
    - Not a regulatory-production reserving system
    - Requires actuarial review before business use
---

# Chainladder Reserving

Use this skill when an agent needs the `actuarial.reserve.chainladder` tool from `actuarial_cli_hub`.

## Command

```bash
actuary reserve chainladder --help
```

## Artifact Contract

- `deterministic_result`
- `diagnostics`
- `explanation_markdown`

## Safety Notes

- Treat outputs as actuarial analysis aids, not signed actuarial opinions.
- Keep upstream repositories and downstream consumers read-only unless a separate task explicitly scopes changes there.
