import logging
from peewee import IntegrityError, JOIN

from bard.providers import providers
from bard.util.info import select_best_series
from bard.models.series import Series
from bard.models.season import Season
from bard.models.episode import Episode
from bard.models.torrent import Torrent
from bard.models.media import Media

log = logging.getLogger(__name__)


def scan_library():
    log.info('Performing a full library scan')

    count = 0
    for series in Series.select():
        count += update_series_media(series)
    return count


def import_library():
    from bard.tasks.series import update_series

    for series in providers.library.get_all_series():
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
    count = 0

    library_series = providers.library.find_series_info(series.name)
    if not library_series:
        results = providers.library.search_series(series.name)
        if len(results) == 1:
            library_series = {'title': results[0].title}
        else:
            log.warning('Failed to find library series for %s', series.name)
            return 0

    library_media = providers.library.find_series_media(library_series['title'])

    episodes = Episode.select().join(Season).where(
        (Season.series == series)
    )
    for episode in episodes:
        if int(episode.season.number) not in library_media:
            continue

        if int(episode.number) not in library_media[int(episode.season.number)]:
            continue

        medias = library_media[int(episode.season.number)][int(episode.number)]

        if medias:
            # TODO: check if this matches our format/resolution first>
            # If we haven't marked this episode as downloaded yet, we do that now
            if episode.state != int(Episode.State.DOWNLOADED):
                episode.state = int(Episode.State.DOWNLOADED)
                episode.save()

                providers.notify.episode_downloaded(episode)

            try:
                for media in medias:
                    media.episode = episode
                    media.save()
                    count += 1
            except IntegrityError:
                continue

    return count


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
