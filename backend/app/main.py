from fastapi import APIRouter, FastAPI

from app.bodyweight.router import router as bodyweight_router
from app.exercises.router import router as exercises_router


def _health_router() -> APIRouter:
    """Router with the liveness endpoint."""
    router = APIRouter()

    @router.get("/health")
    def health() -> dict[str, str]:
        """Report that the API is up."""
        return {"status": "ok"}

    return router


def create_app() -> FastAPI:
    """Build the FastAPI application with all routers under /api."""
    app = FastAPI(title="Hybridly")
    for router in (_health_router(), exercises_router, bodyweight_router):
        app.include_router(router, prefix="/api")
    return app


app = create_app()
