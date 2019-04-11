import logging
import requests
from datetime import datetime

from bard.models.series import Series
from bard.models.season import Season
from bard.models.episode import Episode

BASE_URL = 'https://api.tvmaze.com/'

log = logging.getLogger(__name__)


class TVMazeInfoProvider(object):
    def __init__(self, config):
        self.session = requests.Session()

    def get(self, url, *args, **kwargs):
        r = self.session.get(BASE_URL + url, *args, **kwargs)
        r.raise_for_status()
        return r.json()

    @staticmethod
    def _cast_series(obj):
        return Series(
            provider_id=obj['id'],
            name=obj['name'],
            # TODO: clean out html tags
            desc=obj['summary'],
            banner=obj['image']['original'],
            imdb_id=obj['externals']['imdb'],
        )

    @staticmethod
    def _cast_season(obj):
        return Season(
            number=str(obj['number']),
            episode_count=obj['episodeOrder'],
        )

    @staticmethod
    def _cast_episode(obj):
        return Episode(
            number=str(obj['number']),
            name=obj['name'],
            desc=obj['summary'],
            airdate=datetime.strptime(obj['airstamp'].split('+')[0], '%Y-%m-%dT%H:%M:%S'),
        )

    def search_series(self, name):
        results = self.get('search/shows', params={
            'q': name,
        })

        return [self._cast_series(i['show']) for i in results]

    def get_series(self, series_id):
        data = self.get('shows/{}'.format(series_id))
        return self._cast_series(data)

    def get_seasons(self, series_id):
        data = self.get('shows/{}/seasons'.format(series_id))
        return [self._cast_season(i) for i in data]

    def get_episodes(self, series_id, season):
        results = self.get('shows/{}/episodes'.format(series_id))
        return [self._cast_episode(i) for i in results if str(i['season']) == str(season)]
