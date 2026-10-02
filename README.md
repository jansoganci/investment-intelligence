# Investment Intelligence

US equities fundamental-analysis (FA) spine and related research tooling.

## What’s in this repo

- `fa/` — FA stages, pipeline, market price, Final FA
- `tests/` — pytest suite
- `docs/` — stage/status notes
- `schemas/` — contracts
- `ri/` — research/intelligence helpers
- `fixtures/`, `fa_fixtures/` — small test fixtures
- `PROJECT_STATUS.md`, `CHANGELOG.md` — thin status + append-only changelog

## What’s not in this repo

- `fa_data/`, `audit/` runtime evidence packs (kept off-repo; Drive / local box)
- Secrets / `.env`

## Status

Production SoR historically lived on an agent box (`NO_GIT`). This repository is the versioned mirror of **code + tests + docs** only.

Do not treat Final FA colors as trade signals. GREEN ≠ BUY. No live brokerage execution in v1.
