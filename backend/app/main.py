from fastapi import APIRouter, FastAPI


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
    for router in (_health_router(),):
        app.include_router(router, prefix="/api")
    return app


app = create_app()
