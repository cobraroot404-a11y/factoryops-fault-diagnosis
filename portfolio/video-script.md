# Demo video script (target: 3 minutes)

Status: **recording not completed in this delivery** — this environment has
no screen/audio recording capability. This script, plus the exact commands
and pages to show, is provided so the recording can be captured later with
any screen recorder (OBS, Windows Game Bar, QuickTime, etc.). See the note in
the root README for what to do with the finished file.

## 0:00–0:30 — Architecture and healthy operation
- Show `docs/architecture.md`'s implemented-architecture diagram for 5–10s.
- `./scripts/start.sh && ./scripts/migrate.sh && ./scripts/seed.sh && ./scripts/run-simulator.sh`
- Open http://localhost:5173, sign in as the Northgate technician, show the
  Dashboard with 3 machines, all healthy, live charts moving.

## 0:30–1:00 — Fault injection and customer report
- Go to Fault Injection, click Inject on Motor-1 → overheating.
- Sign out, sign in as the Northgate customer.
- Go to Tickets, submit: machine=Motor-1, symptoms="motor keeps stopping".

## 1:00–1:45 — Diagnosis and evidence
- Sign back in as the technician. Show Incidents → the new overheating
  incident opened on Motor-1.
- Open it: point out Observations, Evidence (thresholds + last value, no
  fabricated confidence score), Suspected Causes, Next Checks.
- Show the linked ticket on the incident / the ticket showing `status: linked`.

## 1:45–2:30 — Troubleshooting and fault removal
- Walk through the guided checklist, checking off 2–3 steps as the technician.
- Go back to Fault Injection, click Remove on Motor-1 → overheating.
- Show the simulated temperature chart trending back down.

## 2:30–3:00 — Recovery, measurements, and CI
- Wait for/show the incident move to Resolved with "recovery verified."
- Show `portfolio/reports/measurements-report.md` (or the terminal output of
  `./scripts/collect-measurements.sh`).
- Show the green GitHub Actions run for this commit (Actions tab or the
  README's CI badge/link).

## Additional demonstration clip (separate, not counted in the 3 minutes)
- Stop the diagnosis worker (`docker compose ... stop diagnosis-worker`),
  show the RabbitMQ queue depth growing in the management UI or Grafana.
- Restart it (`docker compose ... start diagnosis-worker`), show the backlog
  drain and exactly one incident (no duplicates).
- Separately, run `./scripts/run-tests.sh --e2e` (or just the poison-message
  test) and show the message landing in `readings.dead-letter` in the
  RabbitMQ UI after bounded retries.

## Capture notes
- Mute/blur anything showing `.env` contents, real file paths with your
  Windows username, or terminal history unrelated to the demo.
- Record at 1080p if possible; keep terminal font large enough to read.
