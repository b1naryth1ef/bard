import logging
import os

from bard.models.media import Media

log = logging.getLogger(__name__)


def prune_missing_media():
    for media in Media.select():
        if not os.path.exists(media.path):
            log.info('Media file %r no longer appears to exist on disk, pruning', media)
            media.delete_instance()
