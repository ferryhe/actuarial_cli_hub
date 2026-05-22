---
name: actuarial-aggregate-loss
description: Use `actuary loss aggregate` from actuarial_cli_hub for Aggregate Loss workflows.
version: 0.1.0
metadata:
  source_tool_id: actuarial.loss.aggregate
  runtime_availability: implemented
  use_cases:
    - Aggregate loss and risk examples
    - Teaching collective risk model workflows
  limitations:
    - DSL declarations must be reviewed by a qualified actuary
    - The roadmap shorthand defaults to Poisson when no frequency family is supplied
---

# Aggregate Loss

Use this skill when an agent needs the `actuarial.loss.aggregate` tool from `actuarial_cli_hub`.

## Command

```bash
actuary loss aggregate --help
```

## Artifact Contract

- `aggregate_result`
- `diagnostics`
- `explanation_markdown`

## Safety Notes

- Treat outputs as actuarial analysis aids, not signed actuarial opinions.
- Keep upstream repositories and downstream consumers read-only unless a separate task explicitly scopes changes there.
