"""
AI Medical Assistant - FastAPI application entrypoint.

Run from the `backend` folder:
  uvicorn app:app --reload --host 127.0.0.1 --port 8000

Open the UI at: http://127.0.0.1:8000/app/
"""
import logging
import os
import socket
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from config import is_sqlite
from database import Base, engine, SessionLocal
from migrations import ensure_runtime_schema
import models.orm  # noqa: F401 — ensure all models register with Base.metadata before create_all
from routes import admin, appointments, auth, chat, diet, doctors, health_data, reports, symptoms
from seed import seed_doctors_if_empty, seed_runtime_defaults

log = logging.getLogger("uvicorn.error")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables on startup (production should use migrations)
    try:
        Base.metadata.create_all(bind=engine)
        ensure_runtime_schema(engine)
        Base.metadata.create_all(bind=engine)
        with SessionLocal() as db:
            seed_doctors_if_empty(db)
            seed_runtime_defaults(db)
    except Exception as exc:
        log.exception("Database connection failed")
        if not is_sqlite():
            log.error(
                "MySQL auth failed or server unreachable. Fix: create backend/.env from .env.example, "
                "set MYSQL_PASSWORD to your MySQL user's password, and ensure the database exists "
                "(run database/schema.sql). Or set DB_BACKEND=sqlite in .env for local file DB."
            )
        raise RuntimeError(
            "Could not connect or initialize the database. See log above and README (MySQL vs SQLite)."
        ) from exc
    yield


app = FastAPI(title="AI Medical Assistant API", version="1.0.0", lifespan=lifespan)

# Public browser UIs may be opened from file:// or another port during dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(symptoms.router)
app.include_router(health_data.router)
app.include_router(doctors.router)
app.include_router(appointments.router)
app.include_router(diet.router)
app.include_router(reports.router)
app.include_router(admin.router)

# Serve the vanilla frontend under /app (same origin as API)
_FRONTEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend"))
if os.path.isdir(_FRONTEND_DIR):
    app.mount("/app", StaticFiles(directory=_FRONTEND_DIR, html=True), name="frontend")


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    """Browsers request /favicon.ico from the site root; redirect to the static SVG under /app/."""
    return RedirectResponse(url="/app/favicon.svg", status_code=307)


@app.get("/")
def root_redirect():
    """Send browsers to the bundled UI."""
    return RedirectResponse(url="/app/")


@app.get("/healthz")
def healthz():
    """Simple readiness probe for deployments."""
    return {"status": "ok"}


def _local_ipv4() -> str:
    """Best-effort LAN IP for sharing the app on the local network."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("8.8.8.8", 80))
        return sock.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        sock.close()


if __name__ == "__main__":
    import uvicorn

    host = "0.0.0.0"
    port = 8000
    lan_ip = _local_ipv4()
    print(f"PC URL: http://127.0.0.1:{port}/app/")
    print(f"Mobile URL: http://{lan_ip}:{port}/app/")
    print(f"Admin URL: http://{lan_ip}:{port}/app/admin.html")
    uvicorn.run("app:app", host=host, port=port, reload=True)
