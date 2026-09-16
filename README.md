# FactoryOps — Automated Customer Fault Diagnosis & Guided Debugging for Cloud-Based Manufacturing

[![CI](https://github.com/cobraroot404-a11y/factoryops-fault-diagnosis/actions/workflows/ci.yml/badge.svg)](https://github.com/cobraroot404-a11y/factoryops-fault-diagnosis/actions/workflows/ci.yml)
[![Deployment validation](https://github.com/cobraroot404-a11y/factoryops-fault-diagnosis/actions/workflows/deploy-validation.yml/badge.svg)](https://github.com/cobraroot404-a11y/factoryops-fault-diagnosis/actions/workflows/deploy-validation.yml)

Latest successful runs actually inspected for this delivery:
- CI: [run 35153247446](https://github.com/cobraroot404-a11y/factoryops-fault-diagnosis/actions/runs/35153247446) — commit `25b6ebc`, all 5 jobs green
- Deployment validation: [run 35153247538](https://github.com/cobraroot404-a11y/factoryops-fault-diagnosis/actions/runs/35153247538) — commit `25b6ebc`, green

> **All telemetry in this project is simulated.** FactoryOps has not been
> validated against physical manufacturing equipment. It is a containerized
> platform **designed for cloud deployment and demonstrated locally** at $0
> additional cost.

> This repository is source-visible, not open source. Viewing and study are
> permitted only under the limited terms of the license. Copying,
> modification, redistribution, and reuse require the owner's prior written
> permission. See [LICENSE](LICENSE) ("SEE LICENSE IN LICENSE").

## What this is

A manufacturing customer reports a machine problem ("motor keeps stopping").
FactoryOps correlates that ticket with simulated telemetry from the relevant
machine, runs an explicit, configurable rule engine (thresholds + hysteresis
+ persistence windows — **not** a trained model, and it never reports a
confidence probability), opens an evidence-backed incident, walks a
technician through a guided troubleshooting checklist, and verifies recovery
once healthy readings are sustained for a configurable window.

## Implemented features

- Sign-in/sign-out, customer + technician roles, backend-enforced multi-factory isolation (two seeded factories).
- Three simulated industrial motors (plus two more in the second factory, for isolation testing) with health, latest readings, and last-seen time.
- Live temperature / current / vibration charts per machine.
- Customer tickets (machine, symptoms, optional error code) auto-correlated to the relevant incident.
- Incidents with severity, status, filtering, and open/resolved timelines.
- Diagnosis view: observations, evidence (thresholds + last value), suspected causes, next checks — no fabricated confidence scores.
- Guided, technician-checkable troubleshooting checklists per fault type.
- Recovery verification after a sustained healthy-observation window.
- Authorized, technician-only demo fault-injection controls (overheating, overload, vibration, missing telemetry).
- Accessible forms (labeled inputs, `role="alert"`/`role="status"` states) and explicit loading/empty/validation/error states throughout.
- Transactional-outbox ingestion, RabbitMQ retry-queue + dead-letter queue with bounded retries, duplicate-safe processing, defined out-of-order behavior, scheduled missing-telemetry checks.
- Prometheus metrics from every service + a provisioned Grafana dashboard.

## Architecture

See [docs/architecture.md](docs/architecture.md) for the full implemented
diagram and the separately-labeled, **unexecuted** proposed AWS diagram (full
mapping + rough costs in [docs/aws-migration.md](docs/aws-migration.md)).

Technology: React + TypeScript, Python FastAPI, PostgreSQL, RabbitMQ (with a
processing queue, a TTL-based retry queue, and a dead-letter queue), a Python
diagnosis worker, a scheduled missing-telemetry checker, a Python telemetry
simulator, Prometheus + Grafana, structured logs, Docker Compose, GitHub
Actions. No Kubernetes, no digital twins, no unrelated microservices, no
paid services.

## $0 cost, existing computer

Everything runs locally via Docker Compose on your own machine. Requirements:
Docker Desktop (or compatible), ~4 GB free RAM for the stack, a few hundred
MB of disk for images/volumes, and internet access only for the one-time
`docker pull` / `pip install` / `npm install` of dependencies — after that,
core execution needs no external APIs or accounts. CI runs on GitHub's free,
GitHub-hosted Actions runners (unlimited free minutes for public
repositories at the time of writing — verify current terms before relying on
this). **No paid cloud resources, domains, hardware, AI APIs, or CI runner
overages were used or are required.**

## Quickstart

```bash
git clone <this repo> && cd factoryops-fault-diagnosis
./scripts/generate-local-env.sh
./scripts/start.sh
./scripts/migrate.sh
./scripts/seed.sh
./scripts/run-simulator.sh
```

Open http://localhost:5173. Demo credentials are written (local only,
gitignored) to `infra/compose/seed-output/demo-credentials.json` by
`scripts/seed.sh` — for example, a Northgate Assembly technician and
customer, and a separate Rivermill Fabrication technician and customer (used
to demonstrate factory isolation).

| URL | Purpose |
|---|---|
| http://localhost:5173 | FactoryOps dashboard |
| http://localhost:8000/docs | FastAPI interactive API docs |
| http://localhost:15672 | RabbitMQ management UI |
| http://localhost:9090 | Prometheus |
| http://localhost:3000 | Grafana (FactoryOps Overview dashboard, pre-provisioned) |

## All documented local commands

| Purpose | Command |
|---|---|
| Generate local secrets | `./scripts/generate-local-env.sh` |
| Start the system | `./scripts/start.sh` |
| Initialize/migrate the database | `./scripts/migrate.sh` |
| Seed accounts and machines | `./scripts/seed.sh` |
| Run the simulator | `./scripts/run-simulator.sh` |
| Inject a fault | `./scripts/inject-fault.sh "Northgate Assembly/Motor-1" overheating` |
| Remove a fault | `./scripts/remove-fault.sh "Northgate Assembly/Motor-1" overheating` |
| List active fault injections | `python scripts/fault_ctl.py list` |
| Run tests | `./scripts/run-tests.sh` (add `--e2e` for the backlog/dead-letter demonstrations) |
| Collect measurements | `./scripts/collect-measurements.sh` |
| Deploy a tested release (local) | `./scripts/deploy.sh [tag]` |
| Roll back | `./scripts/rollback.sh` |
| Stop services (keep data) | `./scripts/stop.sh` |
| Remove project demo data | `./scripts/cleanup-demo-data.sh --yes` |

## Fault types & diagnosis rules

Overheating, overload, excessive vibration (all threshold-based, with
hysteresis + a consecutive-reading persistence window), and missing
telemetry (a scheduled absence check). Rules, thresholds, and window sizes
are plain configuration in [backend/app/config.py](backend/app/config.py) —
see [docs/adr/0002-hysteresis-persistence-windows.md](docs/adr/0002-hysteresis-persistence-windows.md).
Curated troubleshooting knowledge lives in
[backend/app/knowledge.py](backend/app/knowledge.py); it is generic
demonstration guidance, not equipment-specific repair instructions.

## Reliability & security decisions

- **Transactional outbox** for ingestion — see [ADR 0001](docs/adr/0001-transactional-outbox.md).
- **Bounded retries + dead-letter queue** in RabbitMQ (default: 3 attempts, 5s TTL-based retry delay) — see [docs/runbooks/dead-letter-handling.md](docs/runbooks/dead-letter-handling.md).
- **Duplicate-safe processing**: idempotency key at ingestion (unique per machine) + message-id dedup (`processed_messages`) at the worker.
- **One active incident per (machine, fault type)**, enforced by the rule engine's state machine *and* a Postgres partial unique index as a backstop.
- **Backend-enforced factory isolation** on every query (never client-supplied).
- **Separate per-machine credentials** (a hashed API key per machine, not a shared secret).
- **Password hashing** (bcrypt via passlib) and **short-lived JWTs** (default 60 min).
- **Input validation** via Pydantic on every endpoint; **parameterized queries** via SQLAlchemy (no raw string SQL with user input).
- **Restrictive CORS** (only the local frontend origin) and a **request body size limit** (64 KB default).
- **Everything bound to `127.0.0.1`** by default — nothing is exposed beyond localhost.
- **Alembic migrations**, named Docker volumes, and container healthchecks.
- **Secrets never committed** — `.env` is gitignored; `.env.example` documents every variable; `scripts/generate-local-env.sh` generates random local-only values.

### Known limitations
- JWTs are stateless with no server-side revocation list — "logout" is client-side token discard, not server-side invalidation.
- No rate limiting on the login endpoint (out of scope for this delivery).
- Rollback (see [docs/runbooks/rollback.md](docs/runbooks/rollback.md)) only reverts application images, not database migrations.
- Single-instance workers only in this demo profile (no multi-replica consumer testing).

## CI status (GitHub-hosted runners only — see [ADR 0004](docs/adr/0004-no-self-hosted-runner.md))

`.github/workflows/ci.yml` runs on every PR and push to `main`: lint,
backend unit tests, frontend typecheck + tests, dependency audit
(`pip-audit` + `npm audit`), container builds, and a full Docker Compose
integration run — including the deterministic fault-and-recovery tests and
the worker-stop/backlog and poison-message/dead-letter demonstrations.

`.github/workflows/deploy-validation.yml` builds a commit-tagged release,
starts it with Docker Compose **on a fresh, ephemeral GitHub-hosted runner**,
runs migrations, health-checks it, runs a fault-and-recovery smoke test, and
tears everything down. **This is deployment validation in a temporary
environment, not continuous deployment to any persistent host.**

### Verification

Actually run and inspected on this machine (commit `25b6ebc`, 2026-09-16):

| Suite | Result |
|---|---|
| Rule-engine unit tests (`tests/worker`, no DB/broker needed) | 6/6 passed |
| Backend/API integration tests (`tests/backend`, live Postgres + RabbitMQ + workers) | 18/18 passed |
| e2e demonstrations (`tests/e2e`: worker-stop/backlog recovery, poison→dead-letter) | 2/2 passed |
| Frontend tests (`npm run test`, Vitest) | 3/3 passed |
| Frontend typecheck / lint / build | clean, 0 errors |
| `pip-audit` (backend + worker + simulator deps) | 0 known vulnerabilities |
| `npm audit --audit-level=high` (frontend deps) | 0 vulnerabilities |
| Local `scripts/deploy.sh` → health check | verified: backend healthy after deploy |
| Local `scripts/rollback.sh` → health check | verified: rolled back to the prior release tag and healthy |

All 29 automated tests pass. The same suites run automatically in
[`ci.yml`](.github/workflows/ci.yml) on every push/PR, and a fault-and-recovery
smoke test re-runs against a freshly deployed release in
[`deploy-validation.yml`](.github/workflows/deploy-validation.yml).

## Local deployment vs. automated CD

| | Status |
|---|---|
| Local deploy/rollback scripts | ✅ implemented and verified on this machine (see Verification) |
| CI (lint/tests/build/compose-integration) | ✅ implemented, runs on GitHub-hosted runners |
| Deployment validation (ephemeral, ad hoc environment) | ✅ implemented, runs on GitHub-hosted runners |
| Automated CD to *this developer's own machine* triggered by GitHub | ❌ **not implemented** — no self-hosted runner was installed (by explicit choice, see ADR 0004); deploying here is a manual, scripted step |

## Measurements

Real measurements from an actual run against this local stack (commit
`25b6ebc`, 2026-09-16T21:42:52Z) — full methodology, raw data, and
limitations in [portfolio/reports/measurements-report.md](portfolio/reports/measurements-report.md)
and [portfolio/measurements/](portfolio/measurements/):

| Metric | Value |
|---|---|
| Fault injection → detection | 1.062 s |
| Fault removal → verified recovery | 1.157 s |
| Ingest accept success rate (50 readings) | 100% |
| False incidents during a 20s healthy-only simulation | 0 |

Detection requires 3 consecutive breaching readings; recovery requires 5
consecutive healthy readings — a separate, larger window, which is why
recovery is intentionally slower than detection. This is a single local run
on a development machine, not a load test or a statistically averaged
result — see the report for the full caveats.

## Screenshots & recording

Captured from an actual run of this stack (technician/customer flows, real
simulated data, real incident lifecycle):

| | |
|---|---|
| [00-dashboard-all-healthy.png](portfolio/screenshots/00-dashboard-all-healthy.png) | All 3 Northgate motors healthy, live charts |
| [01-dashboard-fault-detected.png](portfolio/screenshots/01-dashboard-fault-detected.png) | Motor-1 shows FAULT after overheating injection |
| [02-incidents-list.png](portfolio/screenshots/02-incidents-list.png) | Incident list, filterable by status/severity |
| [03-incident-diagnosis.png](portfolio/screenshots/03-incident-diagnosis.png) | Observations, evidence, suspected causes |
| [04-incident-checklist.png](portfolio/screenshots/04-incident-checklist.png) | Guided troubleshooting checklist |
| [05-fault-injection-controls.png](portfolio/screenshots/05-fault-injection-controls.png) | Technician-only fault injection controls |
| [06-tickets-linked.png](portfolio/screenshots/06-tickets-linked.png) | Customer ticket auto-linked to the open incident |
| [07-incidents-resolved.png](portfolio/screenshots/07-incidents-resolved.png) | Incident list after resolution |
| [08-incident-recovery-verified.png](portfolio/screenshots/08-incident-recovery-verified.png) | Recovery verified after the healthy window |
| [09-factory-isolation-rivermill.png](portfolio/screenshots/09-factory-isolation-rivermill.png) | A Rivermill Fabrication technician sees only Rivermill's Motor-A/Motor-B — proof of factory isolation |

The 3-minute demo recording described in
[portfolio/video-script.md](portfolio/video-script.md) was **not recorded**
as part of this delivery — this environment has no screen/audio recording
capability. The script and shot list are provided so it can be captured
later with any screen recorder; this is explicitly flagged as incomplete
rather than fabricated.

## Cloud positioning

FactoryOps is a containerized manufacturing platform **designed for cloud
deployment and demonstrated locally**. See
[docs/architecture.md](docs/architecture.md) for the implemented local
diagram and the separately-labeled, unexecuted proposed AWS diagram, and
[docs/aws-migration.md](docs/aws-migration.md) for the full service mapping,
rough costs, and tradeoffs. **No AWS resources were provisioned and no cloud
integration tests were run.**

## Repository structure

```
frontend/          React + TypeScript dashboard
backend/           FastAPI app, Alembic migrations, seed script
worker/            Outbox relay, diagnosis worker, missing-telemetry checker
simulator/         Simulated telemetry generator
infra/compose/     Docker Compose, Prometheus config, Grafana provisioning
tests/             backend (integration), worker (unit), e2e (demonstrations)
scripts/           every documented local command
docs/              architecture, AWS migration, ADRs, runbooks
portfolio/         screenshots, measurements, reports, video script, recruiter blurb
.github/workflows/ CI + deployment validation
```

## Commit identity & licensing

Every commit in this repository is authored and committed as **Gautham**,
the sole human contributor — no AI/bot co-authorship or automated commits
were used to build this project (generated CI artifacts, such as test
reports, are produced by workflow runs, not committed back by a bot).

Licensed under a proprietary source-visible license — see [LICENSE](LICENSE)
(SPDX identifier: `SEE LICENSE IN LICENSE`) and
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) for third-party components.

## Current local status

<!-- STATUS_START -->
Status to be filled in after final verification and cleanup (see below): is
the local demo currently running, and how to restart it.
<!-- STATUS_END -->
