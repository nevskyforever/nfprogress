# Local acceptance

Run `scripts/maintenance/local_acceptance.sh` from any directory in the
checkout:

- `quick` checks the diff, changed Python syntax, shell syntax, and workflow
  YAML.
- `backend` starts a uniquely named PostgreSQL 16 Docker container bound only
  to IPv4 loopback, then runs focused schema, legal, sync, and backend
  regressions plus the real encrypted-blob backup/restore preflight.
- `frontend` runs the historical metadata Vitest set, typecheck, production
  build, and the local Chromium stages, account, and encrypted-workspace
  acceptance flows.
- `prepush` runs the static, frontend, and backend modes in sequence.

The backend modes require Docker Engine and Python test dependencies. Each run
generates a new PostgreSQL password locally, keeps the database DSN in the
process environment, and stops only the task container after verifying its
ownership label and image. It does not create named volumes or use a configured
application database. The frontend modes require the frontend npm dependencies
and Playwright Chromium; browser tests use temporary profiles and local API
fixtures.

On Apple Silicon, Docker runs the PostgreSQL image for the host architecture.
This does not establish Linux x86-64 Chromium compatibility; report that check
separately unless verified in an isolated x86-64 Linux environment.
