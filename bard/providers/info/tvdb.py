import logging

from pytvdbapi import api

from bard.models.series import Series, SeriesMetadata
from bard.models.season import SeasonMetadata
from bard.models.episode import EpisodeMetadata


log = logging.getLogger(__name__)

STATUS_MAP = {
    'Ended': Series.AirStatus.ENDED,
    'Continuing': Series.AirStatus.CONTINUING,
}


class TVDBInfoProvider(object):
    name = 'tvdb'

    def __init__(self, config):
        self.client = api.TVDB(config.get('api_key', 'B43FF87DE395DF56'))
        self.language = config.get('language', 'en')

    @staticmethod
    def cast_series(obj):
        obj.update()

        series = SeriesMetadata(
            provider_ids={'tvdb': int(obj.id), 'imdb': obj.IMDB_ID},
            status=STATUS_MAP.get(obj.Status, Series.AirStatus.UNKNOWN),
            name=obj.SeriesName,
            desc=obj.Overview,
            network=obj.Network,
            content_rating=obj.ContentRating,
            banner=obj.banner,
            poster=obj.poster,
        )

        return series

    @staticmethod
    def cast_season(obj):
        return SeasonMetadata(
            number=str(obj.season_number),
            episode_count=len(obj)
        )

    @staticmethod
    def cast_episode(obj):
        return EpisodeMetadata(
            number=str(obj.EpisodeNumber),
            name=obj.EpisodeName,
            desc=obj.Overview,
            airdate=obj.FirstAired or None,
            imdb_id=obj.IMDB_ID,
        )

    def search_series(self, name):
        q = self.client.search(name, self.language)

        results = []
        for result in q:
            try:
                results.append(self.cast_series(result))
            except Exception:
                log.exception('Failed to parse search result %s', result)
                continue
        return results

    def get_series(self, id):
        return self.cast_series(self.client.get_series(id, self.language))

    def get_seasons(self, id):
        obj = self.client.get_series(id, self.language)
        obj.update()

        result = []
        for season in obj.seasons.values():
            result.append(self.cast_season(season))
        return filter(bool, result)

    def get_episodes(self, id, season):
        obj = self.client.get_series(id, self.language)
        obj.update()

        result = []
        for episode in obj.seasons[int(season)].episodes.values():
            result.append(self.cast_episode(episode))
        return filter(bool, result)

    def find_by_external(self, provider_ids):
        return None
