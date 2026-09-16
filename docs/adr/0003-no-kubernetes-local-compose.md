# ADR 0003: Docker Compose, not Kubernetes, for local deployment

## Status
Accepted

## Context
The project must run at $0 additional cost on the developer's existing
computer, and the brief explicitly excludes Kubernetes, digital twins, and
unrelated microservices.

## Decision
Use Docker Compose (already free with Docker Desktop) to orchestrate
Postgres, RabbitMQ, the backend, three worker processes, the simulator, the
frontend, Prometheus, and Grafana as a single local stack. Named Docker
volumes provide persistence; `docker compose` healthchecks gate startup
ordering.

## Consequences
- No cluster to operate, no additional licensing, no learning-curve tax for a
  project scoped to run on one machine.
- The proposed AWS migration (`docs/aws-migration.md`) would move workloads to
  ECS Fargate rather than EKS, for the same reason — this is a deliberate,
  documented choice, not an oversight.
- Horizontal scaling of the diagnosis worker (running multiple replicas) is
  possible with Compose (`docker compose up --scale diagnosis-worker=N`) but
  is not required for a single-developer local demo and is not exercised
  here.
