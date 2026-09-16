# Runbook: cleanup

## Stop services, keep data

```bash
./scripts/stop.sh
```

Stops all FactoryOps containers. Named Docker volumes (`pgdata`,
`rabbitmq_data`, `prometheus_data`, `grafana_data`) are untouched — restart
with `./scripts/start.sh` and everything (accounts, machines, incident
history) is exactly as you left it.

## Remove demo data explicitly (destructive, requires confirmation)

```bash
./scripts/cleanup-demo-data.sh --yes
```

Truncates every FactoryOps table (factories, users, machines, readings,
incidents, tickets, fault injections, outbox/queue bookkeeping) and deletes
the local `infra/compose/seed-output/` credentials file. This does **not**
touch source code, git history, or the containers/images themselves — re-run
`./scripts/seed.sh` afterward to get a fresh demo world.

## Full teardown (remove containers + volumes)

```bash
docker compose -f infra/compose/docker-compose.yml --env-file .env --profile simulate down -v
```

This is the only command in this project that deletes the Postgres/RabbitMQ/
Grafana/Prometheus **volumes**. Use it when you want a completely clean slate
(equivalent to never having run the project). It does not remove built
images from your local Docker cache — run `docker image prune` yourself if
you also want those gone (this project never does that automatically, to
avoid touching images unrelated to FactoryOps).

## What is never deleted by any script here

- The GitHub repository.
- Your local git checkout, history, or any file tracked in git.
- Any Docker image, container, network, or volume not created by this
  project's `docker-compose.yml` (all FactoryOps resources are scoped under
  the `factoryops` Compose project name).
