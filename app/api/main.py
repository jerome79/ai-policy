from pathlib import Path

from fastapi import FastAPI

from app.api.routes.workflow_routes import build_workflow_router
from app.bootstrap import build_runner


def create_app() -> FastAPI:
    app = FastAPI(title="Policy Governed Agent Runtime", version="0.1.0")
    runner = build_runner(base_path=Path(__file__).resolve().parents[2])
    app.include_router(build_workflow_router(runner))
    return app


app = create_app()
