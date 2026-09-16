# Recruiter-facing summary

**FactoryOps — Automated Customer Fault Diagnosis for Cloud-Based
Manufacturing** is a full-stack, containerized platform I designed and built
end-to-end: a React/TypeScript dashboard, a Python/FastAPI backend, a
RabbitMQ-based event pipeline with a transactional outbox and dead-letter
handling, and a rule-based diagnosis engine that correlates customer trouble
tickets with simulated industrial-motor telemetry, surfaces evidence-backed
incidents, and verifies recovery — all running locally via Docker Compose
with a GitHub Actions CI pipeline and an ephemeral deployment-validation
workflow. All telemetry is clearly labeled synthetic; the project has not
been validated on physical equipment.

## Résumé bullet (verified capabilities only)

> Designed and built FactoryOps, a containerized fault-diagnosis platform
> (React/TypeScript, FastAPI, PostgreSQL, RabbitMQ, Prometheus/Grafana)
> implementing a transactional-outbox ingestion pipeline, a configurable
> hysteresis/persistence-window rule engine for 4 fault types, role-based
> multi-tenant factory isolation, and bounded-retry dead-letter handling;
> verified via automated CI (unit, integration, and deterministic
> fault-and-recovery tests) and an ephemeral GitHub Actions deployment
> validation workflow — see the [passing CI run](https://github.com/cobraroot404-a11y/factoryops-fault-diagnosis/actions/runs/35153247446).

Repository: https://github.com/cobraroot404-a11y/factoryops-fault-diagnosis
(see the root [README.md](../README.md) for the live CI badge and full
verification details).
