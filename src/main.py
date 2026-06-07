import logging
import os
import sys

from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, os.path.dirname(__file__))

from config import Config
from auth import TokenManager
from client import ProcareClient
from sync.api_client import ApiClient
from sync.runner import run_full_sync

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


def main():
    config = Config()
    config.validate()

    token_manager = TokenManager(config)
    client = ProcareClient(config, token_manager)
    api = ApiClient(config.api_url, config.ingest_token)

    try:
        if config.run_once:
            logger.info("RUN_ONCE=true, running single sync")
            counts = run_full_sync(client, api, config)
            logger.info("Sync complete: %s", counts)
            return

        from apscheduler.schedulers.blocking import BlockingScheduler
        from datetime import datetime

        def sync_job():
            logger.info("Scheduled sync triggered")
            try:
                counts = run_full_sync(client, api, config)
                logger.info("Sync complete: %s", counts)
            except Exception as e:
                logger.error("Sync failed: %s", e, exc_info=True)

        scheduler = BlockingScheduler()
        scheduler.add_job(
            sync_job,
            "interval",
            minutes=config.sync_interval_minutes,
            next_run_time=datetime.now(),
        )
        logger.info("Scheduler starting, interval=%d minutes", config.sync_interval_minutes)
        try:
            scheduler.start()
        except (KeyboardInterrupt, SystemExit):
            logger.info("Shutting down scheduler")
            scheduler.shutdown()
    finally:
        client.close()
        api.close()


if __name__ == "__main__":
    main()