import os
import logging
from collections import defaultdict

from peewee import JOIN

from bard.providers import providers
from bard.util.info import select_best_series
from bard.models.series import Series
from bard.models.season import Season
from bard.models.episode import Episode
from bard.models.torrent import Torrent
from bard.models.media import Media

log = logging.getLogger(__name__)


def get_path_size_on_disk(path):
    try:
        return os.path.getsize(path)
    except OSError:
        return None


def scan_library():
    log.info('Performing a full library scan')

    count = 0
    for series in Series.select():
        count += update_series_media(series)
    return count


def import_library():
    from bard.tasks.series import update_series

    for series in providers.library.get_all_series_names():
        if Series.select().where(Series.name == series).exists():
            continue

        result = select_best_series(providers.info, series.name)
        if result:
            log.debug('Found result for %s, adding to library', series.name)
            result.save()
            update_series(result)
        else:
            log.debug('No result found for %s', series.name)


def update_series_media(series):
    # Grab all the media files for this series and group them by season/episode
    seasons = defaultdict(lambda: defaultdict(list))
    for media in providers.library.get_all_series_media(series):
        seasons[media.season_number][media.episode_number].append(media)

    episodes = Episode.select().join(Season).where(
        (Season.series == series)
    )
    episodes_to_notify = []
    for episode in episodes:
        if episode.season.number not in seasons:
            continue

        if episode.number not in seasons[episode.season.number]:
            continue

        medias = seasons[episode.season.number][episode.number]
        if not medias:
            continue

        # TODO: check if this matches our format/resolution first?
        # If we haven't marked this episode as downloaded yet, we do that now
        if episode.state != int(Episode.State.DOWNLOADED):
            episode.state = int(Episode.State.DOWNLOADED)
            episode.save()

            episodes_to_notify.append(episode)

        for media_metadata in medias:
            try:
                media = Media.get(library_id=media_metadata.library_id)
                media.update_from_metadata(media_metadata)
                media.save()
            except Media.DoesNotExist:
                Media.from_metadata(episode, media_metadata)

    # Send the episodes we've downloaded to the notify provider. This is done in
    #  bulk to allow our notify provider to special case bulk series loads without
    #  spamming notifications.
    providers.notify.episodes_downloaded(episodes_to_notify)


def update_missing_items():
    # This task is primarly responsible for pulling in `media` items from our
    #  external library after they have been downloaded and processed by bard.
    #  There is some period of lag time between when bard fully extracts a torrent
    #  and when the library detects and imports the extracted media. While bard
    #  performs regular scans against the remote library to pickup any missing
    #  media, these are slow and only run occasionally. To reduce the latency
    #  of bard detecting media, we look for all series that have an episode with
    #  a torrent that has been processed, but do not have a corresponding media
    #  item yet.
    dirty_series = Series.select(Series) \
        .join(Season).join(Episode).switch(Episode) \
        .join(Media, JOIN.LEFT_OUTER).switch(Episode) \
        .join(Torrent) \
        .where(
            (Torrent.processed >> True) & (Media.id >> None)
        ).group_by(Series)

    for series in dirty_series:
        update_series_media(series)
