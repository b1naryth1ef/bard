import logging

from bard.providers import providers
from bard.models.series import Series
from bard.models.season import Season

log = logging.getLogger(__name__)


def update_all_series():
    for series in Series.select():
        update_series(series)


def update_series(series):
    """
    Attempts to update all metadata about a series (seasons, episodes, media, etc).
    """
    from bard.tasks.season import update_season
    from bard.tasks.library import update_series_media
    log.info('Performing update on series %s (%s)', series.name, series.id)

    # Update the series metadata
    series_info = providers.info.get_series(series)
    series.update_from_metadata(series_info)
    series.save()

    seasons = providers.info.get_seasons(series)
    for season_info in seasons:
        season = None
        try:
            # If we have an existing season, just update that
            season = Season.get(series=series, number=season_info.number)
            season.update_from_metadata(season_info)
            season.save()
        except Season.DoesNotExist:
            season = Season.from_metadata(series, season_info)

        update_season(season)

    update_series_media(series)
