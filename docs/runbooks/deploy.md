# Runbook: local deploy

FactoryOps has no automated deployment to any persistent environment (see
[ADR 0004](../adr/0004-no-self-hosted-runner.md)). Deploying means running it
on your own machine.

## Steps

```bash
./scripts/generate-local-env.sh   # creates .env with random local secrets (idempotent)
./scripts/deploy.sh                # builds+tags a release from the current git commit,
                                    # starts postgres+rabbitmq, migrates, starts the
                                    # rest of the stack, health-checks, records the
                                    # deployed version to infra/compose/CURRENT_RELEASE
./scripts/seed.sh                  # first deploy only (or after cleanup-demo-data.sh)
./scripts/run-simulator.sh         # optional: start generating simulated telemetry
```

`scripts/deploy.sh` accepts an optional explicit tag:
`./scripts/deploy.sh v1.2.0` — otherwise it uses the current git short SHA.

## What "health-checked" means here

The script polls `GET /health` on the backend until it returns 200 (up to
~60s), then writes the release tag to `infra/compose/CURRENT_RELEASE`. It does
not currently verify the frontend or worker containers beyond Docker's own
`restart: unless-stopped` supervision — see Limitations below.

## Limitations

- No blue/green or canary — this stops nothing and simply builds+starts new
  images (Compose recreates changed containers in place).
- Database migrations are applied unconditionally by `alembic upgrade head`
  before the app starts; there's no automated "dry run" against production
  data because there is no production data — this is a local demo.
- If migrations partially fail, you must resolve the database state by hand
  before retrying (Alembic tracks the last successful revision).
