import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.config import ApiConfig
from api.db import init_db
from api.heartbeat import start_heartbeat
from api.notifier import build_notifiers
from api.routers import activities, alerts, contacts, ingest, kids, rooms, staff

logger = logging.getLogger(__name__)


def create_app(config: ApiConfig | None = None) -> FastAPI:
    config = config or ApiConfig()
    app = FastAPI(
        title="procare-api",
        version="0.1.0",
        description="Read API + MCP server + ingest endpoints for procare-ingest data.",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[o.strip() for o in config.cors_origins.split(",")] if config.cors_origins else ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.state.config = config
    app.state.notifiers = build_notifiers()
    app.state.heartbeat_task = None

    @app.on_event("startup")
    async def _startup():
        init_db(config.sqlite_path)
        app.state.heartbeat_task = start_heartbeat(app)

    @app.on_event("shutdown")
    async def _shutdown():
        task = app.state.heartbeat_task
        if task and not task.done():
            task.cancel()

    @app.get("/healthz", tags=["meta"])
    def healthz():
        return {"status": "ok"}

    @app.get("/", tags=["meta"])
    def root():
        return {"service": "procare-api", "version": app.version, "mcp": "/mcp"}

    app.include_router(kids.router)
    app.include_router(rooms.router)
    app.include_router(contacts.router)
    app.include_router(staff.router)
    app.include_router(activities.router)
    app.include_router(ingest.router)
    app.include_router(alerts.router)
    app.include_router(alerts.ingest_router)

    try:
        from api.mcp_server import build_mcp_server
        mcp = build_mcp_server()
        app.mount("/mcp", mcp.streamable_http_app())
        logger.info("MCP server mounted at /mcp")
    except ImportError as e:
        logger.warning("mcp package not installed; MCP endpoint disabled (%s)", e)

    return app


app = create_app()


def main():
    import uvicorn
    config = ApiConfig()
    logging.basicConfig(
        level=config.log_level.upper(),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    uvicorn.run("api.main:app", host=config.host, port=config.port, log_level=config.log_level)


if __name__ == "__main__":
    main()