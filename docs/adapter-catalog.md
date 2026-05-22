# Adapter Catalog

This catalog summarizes the initial actuarial OSS map. Registry YAML files are authoritative for machine-readable fields.

| Target | Domain | Class | Status | Priority | First conversion form |
| --- | --- | --- | --- | --- | --- |
| chainladder-python | P&C reserving | python-library | manifested | P0 | Full wrapper: `actuary reserve chainladder`. |
| aggregate | Aggregate loss / risk | python-dsl | manifested | P0 | Full wrapper: `actuary loss aggregate`. |
| cashflower | Cash-flow modeling | python-model-runner | cataloged | P1 | Model-run wrapper. |
| lifelib | Life / IFRS 17 templates | python-model-runner | cataloged | P1/P2 | Template runner. |
| modelx | Model graph/runtime support | python-model-runner | cataloged | P1/P2 | Supporting model runtime for lifelib-like workflows. |
| MortalityTables.jl | Mortality tables | julia-adapter | cataloged | P2 | Optional Julia JSON bridge. |
| lifecontingencies | Life contingencies | r-adapter | cataloged | P2 | Optional Rscript JSON bridge. |
| insurancerating | Pricing / rating | r-adapter | cataloged | P2 | Optional Rscript JSON bridge. |
| FASLR | Reserving app/workbench | application-spike | cataloged | P3 | Catalog first; wrapper only after public API spike. |
| Loss Data Analytics | Education/reference/data | reference-pack | external-reference | P3 | Reference/data pack, not a calculation wrapper. |
| actuarial-foss | Actuarial OSS catalog | catalog-importer | cataloged | P0/P1 | Catalog importer / registry seed. |

## Runtime implementation order

1. P0 full Python wrappers prove the artifact and error-envelope contract.
2. P1 model runners prove directory/template inputs.
3. P2 R/Julia adapters prove optional runtime boundaries without heavy core installs.
4. P3 references and applications prove the hub can catalog useful non-wrapper sources honestly.
