from __future__ import annotations

from fastapi import FastAPI

from backend.api.routes import ai_router, health_router, platform_router, scrna_router, workflow_runs_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="Omics Intelligent Analysis Platform API",
        version="0.1.0",
        description="API layer for controlled omics workflow execution.",
    )
    app.include_router(ai_router)
    app.include_router(health_router)
    app.include_router(platform_router)
    app.include_router(scrna_router)
    app.include_router(workflow_runs_router)
    return app


app = create_app()
