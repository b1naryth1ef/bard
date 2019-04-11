import logging
import requests
from datetime import datetime
from collections import OrderedDict

from bard.models.series import Series, SeriesMetadata
from bard.models.season import SeasonMetadata
from bard.models.episode import EpisodeMetadata

BASE_URL = 'https://api.tvmaze.com/'

SUPPORTED_EXTERNAL_SERIVCES = OrderedDict([
    ('imdb', 'imdb'),
    ('tvdb', 'thetvdb'),
    ('tvrage', 'tvrage'),
])

STATUS_MAP = {
    'Running': Series.AirStatus.CONTINUING,
    'Ended': Series.AirStatus.ENDED,
}

log = logging.getLogger(__name__)


class TVMazeInfoProvider(object):
    name = 'tvmaze'

    def __init__(self, config):
        self.session = requests.Session()

    def get(self, url, *args, **kwargs):
        r = self.session.get(BASE_URL + url, *args, **kwargs)
        r.raise_for_status()
        return r.json()

    @staticmethod
    def _cast_series(obj):
        provider_ids = {'tvmaze': obj['id']}
        for service, service_name in SUPPORTED_EXTERNAL_SERIVCES.items():
            if service_name in obj['externals']:
                provider_ids[service] = obj['externals'][service_name]

        return SeriesMetadata(
            provider_ids=provider_ids,
            status=STATUS_MAP.get(obj['status'], Series.AirStatus.UNKNOWN),
            name=obj['name'],
            # TODO: clean out html tags
            desc=obj['summary'],
            network=(obj['network'] or {}).get('name'),
            content_rating=None,
            banner=(obj['image'] or {}).get('original'),
            poster=None,
        )

    @staticmethod
    def _cast_season(obj):
        return SeasonMetadata(
            number=str(obj['number']),
            episode_count=obj['episodeOrder'],
        )

    @staticmethod
    def _cast_episode(obj):
        return EpisodeMetadata(
            number=str(obj['number']),
            name=obj['name'],
            desc=obj['summary'],
            airdate=datetime.strptime(obj['airstamp'].split('+')[0], '%Y-%m-%dT%H:%M:%S'),
            imdb_id=None,
        )

    def search_series(self, name):
        results = self.get('search/shows', params={
            'q': name,
        })

        return [self._cast_series(i['show']) for i in results]

    def find_by_external(self, external_ids):
        for service, service_key in SUPPORTED_EXTERNAL_SERIVCES.items():
            if service not in external_ids:
                continue

            try:
                result = self.get('lookup/shows', params={
                    service_key: external_ids[service]
                })
                return self._cast_series(result)
            except:
                continue

    def get_series(self, series_id):
        data = self.get('shows/{}'.format(series_id))
        return self._cast_series(data)

    def get_seasons(self, series_id):
        data = self.get('shows/{}/seasons'.format(series_id))
        return [self._cast_season(i) for i in data]

    def get_episodes(self, series_id, season):
        results = self.get('shows/{}/episodes'.format(series_id))
        return [self._cast_episode(i) for i in results if str(i['season']) == str(season)]
