import sched
import time
import logging
from datetime import datetime

from bard.models.task import Task
from bard.tasks.episode import find_episodes
from bard.tasks.torrent import update_torrents, prune_torrents
from bard.tasks.library import scan_library, update_missing_items
from bard.tasks.series import update_all_series
from bard.tasks.media import prune_missing_media

scheduler = sched.scheduler(time.time, time.sleep)
log = logging.getLogger(__name__)


def _seconds_until(future_dt):
    return (datetime.utcnow() - future_dt).seconds


def register_repeating_task(seconds, func):
    def wrap():
        log.info('Running task %s', func.__name__)
        try:
            return func()
        except Exception:
            log.exception('Error in repeating task %s: ', func.__name__)
        finally:
            Task.save_run(func.__name__)
            scheduler.enter(seconds, 1, wrap, ())

    next_run = Task.get_next_run(func.__name__, seconds)
    if next_run < datetime.utcnow():
        scheduler.enter(0, 1, wrap, ())
    else:
        scheduler.enter(_seconds_until(next_run), 1, wrap, ())


def init_cron():
    register_repeating_task(60, update_torrents)
    register_repeating_task(60, update_missing_items)
    register_repeating_task(60 * 30, find_episodes)
    register_repeating_task(60 * 60 * 2, prune_torrents)
    register_repeating_task(60 * 60 * 24, prune_missing_media)
    register_repeating_task(60 * 60 * 24, scan_library)
    register_repeating_task(60 * 60 * 24, update_all_series)
