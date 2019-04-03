import sched
import time
import logging

from bard.tasks.episode import find_episodes
from bard.tasks.torrent import update_torrents
from bard.tasks.library import scan_library, update_missing_items
from bard.tasks.series import update_all_series

scheduler = sched.scheduler(time.time, time.sleep)
log = logging.getLogger(__name__)


def register_repeating_task(seconds, func):
    def wrap():
        log.info('Running task %s', func.__name__)
        try:
            return func()
        except Exception:
            log.exception('Error in repeating task %s: ', func.__name__)
        finally:
            scheduler.enter(seconds, 1, wrap, ())
    scheduler.enter(seconds, 1, wrap, ())


register_repeating_task(60, update_torrents)
register_repeating_task(60, update_missing_items)
register_repeating_task(60 * 30, find_episodes)
register_repeating_task(60 * 60 * 24, scan_library)
register_repeating_task(60 * 60 * 24, update_all_series)
