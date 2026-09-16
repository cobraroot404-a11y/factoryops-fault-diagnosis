from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator

from app.config import settings
from app.routers import admin, auth, incidents, machines, telemetry, tickets

app = FastAPI(title="FactoryOps Fault Diagnosis API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list(),
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "X-API-Key"],
)


@app.middleware("http")
async def limit_body_size(request: Request, call_next):
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > settings.max_request_body_bytes:
        return JSONResponse(status_code=413, content={"detail": "Request body too large"})
    return await call_next(request)


Instrumentator().instrument(app).expose(app, endpoint="/metrics")

app.include_router(auth.router)
app.include_router(machines.router)
app.include_router(telemetry.router)
app.include_router(tickets.router)
app.include_router(incidents.router)
app.include_router(admin.router)


@app.get("/health")
def health():
    return {"status": "ok"}
