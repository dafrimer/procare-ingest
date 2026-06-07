import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.config import ApiConfig

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

    @app.get("/healthz", tags=["meta"])
    def healthz():
        return {"status": "ok"}

    @app.get("/", tags=["meta"])
    def root():
        return {"service": "procare-api", "version": app.version}

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