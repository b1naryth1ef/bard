import logging

from bard.providers import providers
from bard.models.media import Media
from bard.models.episode import Episode
from bard.models.season import Season
from bard.models.series import Series

log = logging.getLogger(__name__)


def prune_missing_media():
    series = None
    series_media_ids = None
    for media in (
        Media.select().join(Episode).join(Season).join(Series).order_by(Series.id)
    ):
        if not series or series.id != media.episode.season.series.id:
            series = media.episode.season.series
            series_media_ids = {
                i.library_id
                for i in providers.library.get_all_series_media(
                    media.episode.season.series
                )
            }

        if media.library_id not in series_media_ids:
            log.info("Pruning media file %r (%r)", media, media.path)
            media.delete_instance()
