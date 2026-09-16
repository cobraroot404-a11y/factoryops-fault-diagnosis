# ADR 0004: No self-hosted GitHub Actions runner; ephemeral deployment validation instead

## Status
Accepted

## Context
The original brief offered an optional self-hosted GitHub Actions runner
installed on the developer's machine for automated local CD. A self-hosted
runner is a persistent background service with access to the machine and
(if wired to a deploy job) an environment — a meaningful, hard-to-fully-undo
change to install for a portfolio project, and one that needs ongoing care
(security updates, making sure untrusted PRs can never reach it).

## Decision
No self-hosted runner is installed. Instead:
1. **CI** (`.github/workflows/ci.yml`) runs entirely on free GitHub-hosted
   runners: lint, unit tests, frontend checks, dependency audit, container
   builds, and a full Docker Compose integration run (including the
   deterministic fault-and-recovery tests and the backlog/dead-letter
   demonstrations) — all inside a single ephemeral job, torn down at the end.
2. **Deployment validation** (`.github/workflows/deploy-validation.yml`) runs
   on every push to `main` (and on manual dispatch): it builds a
   commit-tagged release, brings it up with Docker Compose on a *fresh*
   GitHub-hosted runner, runs migrations, health-checks it, runs a
   fault-and-recovery smoke test against it, and tears everything down. This
   proves the release is deployable and healthy — it does **not** deploy to
   any persistent, long-lived environment.
3. **Local CD** to the developer's own machine remains a manual, scripted
   step (`scripts/deploy.sh` / `scripts/rollback.sh`), documented in
   `docs/runbooks/deploy.md`.

## Consequences
- No always-on runner process to secure, patch, or eventually decommission.
- Untrusted pull requests never execute against any credential-bearing
  environment; every CI job runs in a disposable GitHub-hosted VM.
- "Automated deployment to this machine" is honestly **not** implemented and
  is documented as such everywhere the project's status is summarized (this
  ADR, the README, and the final report). What *is* automated is deployment
  **validation** in a temporary, ephemeral environment plus a scripted,
  human-run local deploy.
