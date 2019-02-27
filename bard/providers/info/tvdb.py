from bard.models.series import Series
from bard.models.season import Season
from bard.models.episode import Episode

from pytvdbapi import api


class TVDBInfoProvider(object):
    def __init__(self, bard, config):
        self.client = api.TVDB(config.get('api_key', 'B43FF87DE395DF56'))
        self.language = config.get('language', 'en')

    @staticmethod
    def cast_series(obj):
        obj.update()

        series = Series(
            provider_id=int(obj.id),
            name=obj.SeriesName,
            desc=obj.Overview,
            network=obj.Network,
            content_rating=obj.ContentRating,
            banner=obj.banner,
            poster=obj.poster,
            imdb_id=obj.IMDB_ID)

        if obj.Status == 'Ended':
            series.status = Series.AirStatus.ENDED
        elif obj.Status == 'Continuing':
            series.status = Series.AirStatus.CONTINUING
        else:
            series.status = Series.AirStatus.UNKNOWN

        return series

    @staticmethod
    def cast_season(obj):
        return Season(
            number=str(obj.season_number),
            episode_count=len(obj)
        )

    @staticmethod
    def cast_episode(obj, season):
        return Episode(
            season=season,
            number=str(obj.EpisodeNumber),
            name=obj.EpisodeName,
            desc=obj.Overview,
            airdate=obj.FirstAired,
            imdb_id=obj.IMDB_ID,
        )

    def search_series(self, name):
        q = self.client.search(name, self.language)

        results = []
        for result in q:
            try:
                results.append(self.cast_series(result))
            except:
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
            result.append(self.cast_episode(episode, season))
        return filter(bool, result)
