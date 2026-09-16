# Architecture

## Implemented (local, Docker Compose) — this is what actually runs

```mermaid
flowchart LR
    subgraph Client
        FE[React + TS dashboard\n(nginx, :5173)]
    end

    subgraph Edge
        SIM[Simulator\n(3+2 simulated motors)]
    end

    subgraph Backend services
        API[FastAPI backend\n:8000]
        RELAY[Outbox relay]
        WORKER[Diagnosis worker]
        CHECK[Missing-telemetry checker]
    end

    subgraph Data
        PG[(PostgreSQL)]
        MQ[[RabbitMQ\nreadings.process / retry / dead-letter]]
    end

    subgraph Observability
        PROM[Prometheus]
        GRAF[Grafana]
    end

    FE -->|REST + JWT| API
    SIM -->|X-API-Key| API
    API -->|reading + outbox row\n(one transaction)| PG
    RELAY -->|poll unpublished| PG
    RELAY -->|publish, confirmed| MQ
    MQ -->|consume| WORKER
    WORKER -->|state + incidents| PG
    CHECK -->|scan last_seen_at| PG
    API -->|/metrics| PROM
    RELAY -->|/metrics| PROM
    WORKER -->|/metrics| PROM
    CHECK -->|/metrics| PROM
    PROM --> GRAF
```

Everything above runs on the developer's own machine via `docker compose`
(see [infra/compose/docker-compose.yml](../infra/compose/docker-compose.yml)).
No cloud account, physical hardware, or paid API is required. All telemetry is
synthetic, produced by [simulator/simulate.py](../simulator/simulate.py).

### Why a transactional outbox

The API's `/telemetry/readings` endpoint writes the `Reading` row and an
`OutboxEvent` row in the **same** database transaction (see
[backend/app/outbox.py](../backend/app/outbox.py)). A separate relay process
polls unpublished outbox rows and only marks them published after RabbitMQ
confirms the publish. If RabbitMQ is down when a reading arrives, the reading
is still durably accepted — it just waits in the outbox until the relay can
deliver it. See [docs/adr/0001-transactional-outbox.md](adr/0001-transactional-outbox.md).

### Why hysteresis + a persistence window

A single threshold crossing never opens an incident. Each fault type has a
`trigger` and a lower `clear` threshold with a dead zone between them, and
requires N consecutive breaching readings before opening an incident and M
consecutive healthy readings before resolving it. See
[docs/adr/0002-hysteresis-persistence-windows.md](adr/0002-hysteresis-persistence-windows.md).

## Proposed AWS architecture (NOT built, NOT deployed, NOT tested)

This diagram is a **design proposal only**. No AWS resources were created for
this project, no billing was enabled, and no cloud integration tests were run
against it. See [docs/aws-migration.md](aws-migration.md) for the full
service-by-service mapping, estimated costs, and tradeoffs.

```mermaid
flowchart LR
    subgraph "AWS (proposed, unexecuted)"
        CF[CloudFront] --> S3[S3 static site\n(frontend build)]
        ALB[Application Load Balancer] --> ECS[ECS Fargate\nbackend + workers]
        ECS --> RDS[(RDS PostgreSQL)]
        ECS --> MQAWS[[Amazon MQ\nor SQS]]
        ECS --> CW[CloudWatch\nmetrics + logs]
        CW --> DASH[CloudWatch/Grafana\ndashboard]
    end
    USER((Browser)) --> CF
    USER --> ALB
```
