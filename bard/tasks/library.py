import logging
from peewee import IntegrityError
from bard import bard
from holster.tasks import task
from bard.util.info import select_best_series
from bard.models.series import Series
from bard.models.season import Season
from bard.models.episode import Episode

log = logging.getLogger(__name__)


@task()
def scan_library():
    log.info('Performing a full library scan')

    count = 0
    for series in Series.select():
        count += update_series_media(series)
    return count


@task()
def import_library():
    from bard.tasks.series import update_series

    for series in bard.providers.library.get_all_series():
        if Series.select().where(Series.name == series).exists():
            continue

        result = select_best_series(bard, series.name)
        if result:
            log.debug('Found result for %s, adding to library', series.name)
            result.save()
            update_series(result)
        else:
            log.debug('No result found for %s', series.name)


@task()
def update_series_media(series):
    count = 0

    library_series = bard.providers.library.find_series_info(series.name)
    if not library_series:
        results = bard.providers.library.search_series(series.name)
        if len(results) == 1:
            library_series = {'title': results[0].title}
        else:
            log.warning('Failed to find library series for %s', series.name)
            return 0

    library_media = bard.providers.library.find_series_media(library_series['title'])

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
                # bard.providers.notify.episode_downloaded(episode)
                episode.state = int(Episode.State.DOWNLOADED)
                episode.save()

            try:
                for media in medias:
                    media.episode = episode
                    media.save()
                    count += 1
            except IntegrityError:
                continue

    return count
