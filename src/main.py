import logging

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

import config
from radarr import get_movie_files
from sonarr import get_episode_files
from transcoder import transcode

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)


def run() -> None:
    logger.info("Starting transcode run...")
    files = get_episode_files() + get_movie_files()
    logger.info(f"Found {len(files)} files to check")

    transcoded = 0
    for path in files:
        if transcode(path):
            transcoded += 1

    logger.info(f"Run complete. Transcoded {transcoded}/{len(files)} files.")


if __name__ == "__main__":
    logger.info(f"Sizarr starting — schedule: {config.SCHEDULE}")

    run()  # run immediately on start

    scheduler = BlockingScheduler()
    scheduler.add_job(run, CronTrigger.from_crontab(config.SCHEDULE))
    scheduler.start()
