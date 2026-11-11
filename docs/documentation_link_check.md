# Documentation Link Check

Check date: 2026-11-11.

## Scope and method

Scanned inline Markdown links in:

- root `README.md`;
- all 32 Markdown files directly under `docs/`; and
- `archive/README.md`.

Relative links were resolved from the containing document. HTTP/HTTPS links were classified as intentionally external and were not fetched. Code-formatted paths and plain-text historical commands are not Markdown links; stale examples among them are recorded in `repository_documentation_audit.md`.

## Result

| Classification | Count |
|---|---:|
| Markdown files scanned | 34 |
| Links checked | 47 |
| Valid internal links | 22 |
| Broken internal links | 0 |
| Intentionally external links | 25 |
| Anchor-only links | 0 |

No broken inline internal Markdown link required correction. External links were classified only; network availability and external-page content were not validated.

## Remaining path risk

Several dated documents contain code-formatted paths or commands that refer to the removed historical `.venv`, absent historical tests, or old machine-specific roots. These are retained as historical operational context and must not be treated as current setup instructions. Use `REPRODUCIBILITY.md` and the root README for current commands.

