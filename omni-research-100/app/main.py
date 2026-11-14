"""Application FastAPI — point d'entrée de OMNI-RESEARCH 100.

Sert l'API réelle ET l'interface web (PWA, responsive Android/ordinateur).
"""
from __future__ import annotations

import os
import re
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

from .api import agents_api, auth, missions, omnibrain, providers_api, settings_api
from .core.config import Settings, get_settings, load_dotenv, reset_settings
from .core.errors import OmniError
from .core.logging_conf import configure_logging, log_event
from .runtime import Runtime, build_runtime

WEB_DIR = Path(__file__).resolve().parent / "web"

# Sources CSP acceptables pour l'embarquement de l'interface. Aucun « ; »,
# retour à la ligne ni caractère de contrôle : impossibilité d'injecter une
# directive ou un en-tête HTTP via la variable d'environnement.
_CSP_SOURCE_RE = re.compile(r"^[A-Za-z0-9'\"*.:/_\- ]{1,200}$")


def frame_ancestors_for(env: str, raw: str | None = None) -> str:
    """Origines autorisées à afficher l'UI dans une iframe.

    Chaîne vide = politique historique stricte (``X-Frame-Options: DENY`` et
    ``frame-ancestors 'none'``). L'assouplissement par ``OMNI_FRAME_ANCESTORS``
    est réservé aux previews / environnements de développement : il est ignoré
    en production.
    """
    if env == "production":
        return ""
    value = (os.getenv("OMNI_FRAME_ANCESTORS", "") if raw is None else raw).strip()
    if not value or value == "'none'" or not _CSP_SOURCE_RE.fullmatch(value):
        return ""
    return value


def create_app(runtime: Runtime | None = None, settings: Settings | None = None,
               **runtime_kwargs: Any) -> FastAPI:
    load_dotenv()
    reset_settings()
    settings = settings or get_settings()
    configure_logging(settings.log_level)

    # Construit immédiatement : l'API fonctionne aussi sans gestionnaire de
    # cycle de vie (TestClient, serveurs WSGI/ASGI minimalistes).
    effective_runtime = runtime or build_runtime(settings, **runtime_kwargs)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.runtime = effective_runtime
        app.state.started_at = time.time()
        log_event("app", "started", env=settings.env,
                  database=settings.database_url.split("://")[0],
                  agents=effective_runtime.registry.validate()["agents"])
        yield
        for task in list(effective_runtime.tasks.values()):
            task.cancel()
        log_event("app", "stopped")

    app = FastAPI(
        title="OMNI-RESEARCH 100",
        version="1.0.0",
        description=("Plateforme de recherche multi-agents : 100 profils, "
                     "10 divisions, 3 modes, 5 connecteurs Internet, "
                     "adaptateur OmniBrain v1."),
        lifespan=lifespan,
        docs_url="/docs", redoc_url="/redoc", openapi_url="/openapi.json",
    )
    app.state.runtime = effective_runtime  # disponible immédiatement pour les tests
    app.state.started_at = time.time()

    origins = [o.strip() for o in os.getenv("OMNI_CORS_ORIGINS", "").split(",")
               if o.strip()]
    app.add_middleware(
        CORSMiddleware, allow_origins=origins, allow_credentials=False,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-OmniBrain-Key",
                       "X-OmniBrain-Contract"],
    )

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        response = await call_next(request)
        allowed_frames = frame_ancestors_for(settings.env)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        if allowed_frames:
            # La directive CSP fait foi ; laisser X-Frame-Options: DENY
            # annulerait l'autorisation dans les navigateurs historiques.
            if "X-Frame-Options" in response.headers:
                del response.headers["X-Frame-Options"]
        else:
            response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; script-src 'self'; style-src 'self'; "
            "img-src 'self' data:; connect-src 'self'; font-src 'self'; "
            "object-src 'none'; base-uri 'self'; frame-ancestors "
            + (allowed_frames or "'none'"),
        )
        return response

    @app.exception_handler(OmniError)
    async def omni_error(_request: Request, exc: OmniError):
        return JSONResponse(status_code=exc.status_code, content=exc.as_dict())

    @app.exception_handler(RequestValidationError)
    async def validation_error(_request: Request, exc: RequestValidationError):
        return JSONResponse(status_code=422, content={
            "error": "validation_error", "message": "Entrée invalide",
            "detail": [{"loc": list(e.get("loc", [])), "msg": e.get("msg", "")}
                       for e in exc.errors()],
        })

    @app.exception_handler(Exception)
    async def unhandled(_request: Request, exc: Exception):
        log_event("app", "unhandled_exception", level="ERROR",
                  error_type=type(exc).__name__)
        return JSONResponse(status_code=500, content={
            "error": "internal_error",
            "message": "Erreur interne (détail dans les journaux serveur)",
        })

    app.include_router(auth.router)
    app.include_router(missions.router)
    app.include_router(agents_api.router)
    app.include_router(providers_api.router)
    app.include_router(settings_api.router)
    app.include_router(omnibrain.router)

    @app.get("/", include_in_schema=False)
    def index():
        return FileResponse(WEB_DIR / "index.html",
                            headers={"Cache-Control": "no-cache"})

    @app.get("/app.js", include_in_schema=False)
    def app_js():
        return FileResponse(WEB_DIR / "app.js", media_type="application/javascript")

    @app.get("/styles.css", include_in_schema=False)
    def styles():
        return FileResponse(WEB_DIR / "styles.css", media_type="text/css")

    @app.get("/manifest.webmanifest", include_in_schema=False)
    def manifest():
        return FileResponse(WEB_DIR / "manifest.webmanifest",
                            media_type="application/manifest+json")

    @app.get("/index.html", include_in_schema=False)
    def index_alias():
        return FileResponse(WEB_DIR / "index.html",
                            headers={"Cache-Control": "no-cache"})

    @app.get("/icon.svg", include_in_schema=False)
    def icon():
        return FileResponse(WEB_DIR / "icon.svg", media_type="image/svg+xml")

    @app.get("/sw.js", include_in_schema=False)
    def service_worker():
        return FileResponse(WEB_DIR / "sw.js", media_type="application/javascript",
                            headers={"Service-Worker-Allowed": "/",
                                     "Cache-Control": "no-cache"})

    @app.get("/api", include_in_schema=False)
    def api_root():
        return {
            "name": "OMNI-RESEARCH 100", "version": "1.0.0",
            "docs": "/docs", "health": "/api/health",
            "endpoints": sorted({r.path for r in app.routes if r.path.startswith("/api")}),
        }

    return app


app = create_app()


def run() -> None:  # pragma: no cover - lancé par uvicorn en production
    import uvicorn
    settings = get_settings()
    uvicorn.run(app, host=settings.host, port=settings.port,
                log_level=settings.log_level.lower())
