from fastapi import APIRouter, FastAPI

from app.activities.router import router as activities_router
from app.bodyweight.router import router as bodyweight_router
from app.coros.router import router as coros_router
from app.exercises.router import router as exercises_router
from app.history import router as history_router
from app.load.service import router as recovery_router
from app.plans.router import router as plans_router
from app.records import router as records_router
from app.routines.router import router as routines_router
from app.templates.router import router as templates_router
from app.workouts.router import router as workouts_router


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
    for router in (
        _health_router(),
        exercises_router,
        bodyweight_router,
        workouts_router,
        templates_router,
        activities_router,
        coros_router,
        history_router,
        plans_router,
        routines_router,
        recovery_router,
        records_router,
    ):
        app.include_router(router, prefix="/api")
    return app


app = create_app()
