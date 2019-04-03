import time
import logging
import requests

from bard.models.series import Series
from bard.models.season import Season
from bard.models.episode import Episode

BASE_URL = 'https://api.themoviedb.org/3/'
IMAGE_URL_FORMAT = 'https://image.tmdb.org/t/p/w500/{}'

log = logging.getLogger(__name__)


class TMDBInfoProvider(object):
    def __init__(self, config):
        self.api_key = config['api_key']
        self.session = requests.Session()
        self.session.params['api_key'] = self.api_key

    def get(self, url, *args, **kwargs):
        r = self.session.get(BASE_URL + url, *args, **kwargs)
        r.raise_for_status()

        if int(r.headers.get('X-RateLimit-Remaining', 0)) <= 1:
            backoff = int(r.headers.get('X-RateLimit-Reset')) - time.time()
            log.warning('Hit TMDB ratelimit, waiting until %s (%ss)', r.headers.get('X-RateLimit-Reset'), backoff + 1)
            time.sleep(backoff + 1)

        return r.json()

    def cast_series(self, obj, with_network=True, with_external_ids=False):
        series = Series(
            provider_id=obj['id'],
            name=obj['name'],
            desc=obj['overview'],
            banner=IMAGE_URL_FORMAT.format(obj['backdrop_path']),
            poster=IMAGE_URL_FORMAT.format(obj['poster_path']),
        )

        if with_external_ids:
            external_ids = self.get('tv/{}/external_ids'.format(obj['id']))
            series.imdb_id = external_ids.get('imdb_id')

        if with_network:
            details = self.get('tv/{}'.format(obj['id']))
            if details['networks']:
                series.network = details['networks'][0]['name']

        return series

    def cast_season(self, obj):
        return Season(
            number=str(obj['season_number']),
            episode_count=obj['episode_count']
        )

    def cast_episode(self, obj):
        # external_ids = self.get(
        #     'tv/{}/season/{}/episode/{}/external_ids'.format(
        #         obj['show_id'],
        #         obj['season_number'],
        #         obj['episode_number']))
        return Episode(
            number=str(obj['episode_number']),
            name=obj['name'],
            desc=obj['overview'],
            airdate=obj['air_date'],
            # imdb_id=external_ids.get('imdb_id'),
        )

    def search_series(self, name, **kwargs):
        obj = self.get('search/tv', params={'query': name})
        return [self.cast_series(series, **kwargs) for series in obj['results']]

    def get_series(self, id):
        return self.cast_series(self.get('tv/{}'.format(id)), with_external_ids=True)

    def get_seasons(self, id):
        obj = self.get('tv/{}'.format(id))
        return [self.cast_season(season) for season in obj['seasons']]

    def get_episodes(self, id, season):
        obj = self.get('tv/{}/season/{}'.format(id, season))
        return [self.cast_episode(episode) for episode in obj['episodes']]
