# Third-Party Notices

FactoryOps itself is licensed under the terms in [LICENSE](LICENSE). It
depends on the open-source components below, each of which remains under its
own license — nothing in FactoryOps's license extends to them, and nothing in
their licenses extends to FactoryOps's own source. Versions match what's
pinned in `backend/requirements.txt`, `worker/requirements.txt`,
`simulator/requirements.txt`, and `frontend/package.json`. Always check the
upstream project for the authoritative, current license text.

## Backend / worker / simulator (Python)

| Package | Typical license |
|---|---|
| FastAPI | MIT |
| Uvicorn | BSD-3-Clause |
| SQLAlchemy | MIT |
| psycopg (v3) | LGPL-3.0 |
| Alembic | MIT |
| Pydantic / pydantic-settings | MIT |
| passlib | BSD-3-Clause |
| bcrypt (python package) | Apache-2.0 |
| PyJWT | MIT |
| pika | BSD-3-Clause |
| prometheus-fastapi-instrumentator | ISC |
| prometheus-client | Apache-2.0 |
| httpx | BSD-3-Clause |
| pytest / pytest-timeout | MIT |
| ruff | MIT |
| pip-audit | Apache-2.0 |

## Frontend (npm)

| Package | Typical license |
|---|---|
| React / react-dom | MIT |
| react-router-dom | MIT |
| recharts | MIT |
| Vite | MIT |
| TypeScript | Apache-2.0 |
| Vitest | MIT |
| @testing-library/react, @testing-library/jest-dom | MIT |
| ESLint | MIT |

## Container base images / infrastructure

| Image | Typical license |
|---|---|
| `python:3.12-slim` | Python Software Foundation License (Python itself); Debian packages under their own licenses |
| `node:20-alpine` | MIT (Node.js); Alpine packages under their own licenses |
| `nginx:1.27-alpine` | BSD-2-Clause |
| `postgres:16-alpine` | PostgreSQL License |
| `rabbitmq:3.13-management-alpine` | MPL-2.0 |
| `prom/prometheus` | Apache-2.0 |
| `grafana/grafana-oss` | AGPL-3.0 (Grafana OSS, as of Grafana 10+) |

If you plan to redistribute a built FactoryOps image, review the AGPL-3.0
terms for Grafana specifically (it's used as a separate container here, not
linked into FactoryOps's own code) and the LGPL-3.0 terms for `psycopg`.
