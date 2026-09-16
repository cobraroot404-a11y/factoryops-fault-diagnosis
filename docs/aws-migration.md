# Proposed AWS migration (design only — nothing here was provisioned or tested)

This document maps the locally-implemented FactoryOps architecture onto AWS
managed services. It is a **proposal for discussion**, written to demonstrate
cloud-deployment thinking. No AWS account was used, no resources were
created, and no billing was enabled to produce this project. Treat every cost
figure below as a rough, unverified estimate — always check current AWS
pricing before committing to it.

| Local component | Proposed AWS service | Why | Rough monthly cost (small, single-environment) |
|---|---|---|---|
| React frontend (nginx static build) | S3 + CloudFront | Static hosting, cheap, global CDN | ~$1–5 (S3 storage + low CloudFront egress) |
| FastAPI backend | ECS Fargate (or App Runner) behind an ALB | No servers to patch; scales on demand | ~$30–60 (1 small Fargate task + ALB) |
| Diagnosis worker / outbox relay / missing-telemetry checker | ECS Fargate services (no public ingress) | Same runtime as backend, background workloads | ~$20–40 (2–3 small tasks) |
| PostgreSQL | RDS for PostgreSQL (single-AZ, small instance) | Managed backups/patching | ~$15–30 (db.t4g.micro) |
| RabbitMQ | Amazon MQ for RabbitMQ, **or** replace with SQS + SNS (architecture change) | Amazon MQ keeps the exact same broker semantics (retry queue TTL, DLQ) used locally; SQS would need the retry/DLQ pattern re-expressed using SQS-native redrive policies | ~$15–35 (Amazon MQ mq.t3.micro) or a few dollars with SQS |
| Prometheus + Grafana | Amazon Managed Service for Prometheus + Amazon Managed Grafana, **or** CloudWatch metrics/dashboards | AMP/AMG match the local setup closely; CloudWatch is cheaper but requires re-instrumenting some metrics | ~$10–50 depending on option and retention |
| Secrets (.env values) | AWS Secrets Manager or SSM Parameter Store | Never bake secrets into images | ~$1–5 |
| CI/CD | Keep GitHub Actions; add an OIDC role for a deploy job that pushes images to ECR and updates ECS task definitions | No self-hosted runner or long-lived AWS credentials in CI | GitHub Actions: free tier; ECR: pennies |

**Very rough total for a minimal always-on environment: ~$90–200/month**,
dominated by ECS Fargate + RDS + Amazon MQ running continuously. This could
be reduced significantly by scaling Fargate services to zero outside demo
windows, using RDS on a schedule, or moving to a serverless-first redesign
(API Gateway + Lambda + Aurora Serverless v2 + EventBridge instead of
Fargate + RDS + a dedicated broker) — that redesign is a bigger architectural
change than a lift-and-shift and is out of scope for this document.

## Tradeoffs and open questions

- **Amazon MQ vs. SQS**: Amazon MQ is the closer match to the current
  RabbitMQ-specific retry/DLQ topology; SQS is cheaper and more "serverless"
  but requires redesigning the retry-with-delay pattern around SQS's own
  redrive policy and a separate delay queue.
- **RDS single-AZ vs. Multi-AZ**: single-AZ is what's costed above; production
  would want Multi-AZ for automatic failover, roughly doubling the RDS cost.
- **Secrets and machine credentials**: the local design already hashes
  machine API keys and issues per-machine credentials, which maps directly to
  Secrets Manager-issued credentials in AWS with no architecture change.
- **Networking**: the local design binds everything to `127.0.0.1`. On AWS,
  only the ALB (frontend/API) would be public; RDS, Amazon MQ, and the worker
  tasks would sit in private subnets — this is a straightforward VPC
  reproduction of the "bind to localhost by default" principle used locally.

No part of this document should be read as "this was tested on AWS." It was
not.
