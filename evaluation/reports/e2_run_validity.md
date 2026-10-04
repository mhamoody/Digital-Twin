# E2 diagnostic run validity

- `lobot-e2-v1-r1`: diagnostic only; invalid because the initial runner treated unconstrained plain output parsing failures as inference failures.
- `lobot-e2-v1-r2`: diagnostic only; invalid for scientific held-out comparison because the runner exposed target/reference metadata in the model input.
- Next clean run: `lobot-e2-v1-r3`.

The frozen protocol remains v1 and unchanged.
