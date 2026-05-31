import logging
import sys

from dotenv import load_dotenv

load_dotenv()

# Add src to path so imports work when running directly
import os
sys.path.insert(0, os.path.dirname(__file__))

from config import Config
from auth import TokenManager
from client import ProcareClient
from db import init_db, get_db
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
    init_db(config)

    token_manager = TokenManager(config)
    client = ProcareClient(config, token_manager)

    try:
        if config.run_once:
            logger.info("RUN_ONCE=true, running single sync")
            with get_db() as db:
                counts = run_full_sync(db, client, config)
            logger.info("Sync complete: %s", counts)
            return

        # Scheduled mode
        from apscheduler.schedulers.blocking import BlockingScheduler
        from datetime import datetime

        def sync_job():
            logger.info("Scheduled sync triggered")
            try:
                with get_db() as db:
                    counts = run_full_sync(db, client, config)
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


if __name__ == "__main__":
    main()
