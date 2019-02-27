import logging
from bard import bard
from holster.tasks import task

from bard.util.info import select_best_series
from bard.models.series import Series
from bard.models.season import Season

log = logging.getLogger(__name__)


@task()
def update_all_series():
    for series in Series.select():
        update_series(series)


@task()
def update_series(series):
    """
    Attempts to update all metadata about a series (seasons, episodes, media, etc).
    """
    from bard.tasks.season import update_season
    from bard.tasks.library import update_series_media
    log.info('Performing update on series %s (%s)', series.name, series.id)

    # TODO: update series metadata here too?

    seasons = bard.providers.info.get_seasons(series.provider_id)
    for season in seasons:
        try:
            # If we have an existing season, just update that
            existing_season = Season.select().where(
                (Season.series == series) &
                (Season.number == season.number)
            ).get()
            existing_season.merge(season)
            season = existing_season
        except Season.DoesNotExist:
            # Otherwise lets use our new season
            season.series = series

        season.save()
        update_season(season)

    update_series_media(series)


@task()
def repair_provider_ids():
    for series in Series.select():
        result = select_best_series(bard, series.name)
        if not result:
            log.warning('Failed to repair provider ID for series %s (%s)', series.name, series.id)
            continue

        if series.provider_id != result.provider_id:
            series.provider_id = result.provider_id
            series.save()
            log.info('Repaired provider_id for series %s (%s)', series.name, series.id)
