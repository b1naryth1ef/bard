import time
import logging
import requests

from bard.models.series import Series, SeriesMetadata
from bard.models.season import SeasonMetadata
from bard.models.episode import EpisodeMetadata

BASE_URL = "https://api.themoviedb.org/3/"
IMAGE_URL_FORMAT = "https://image.tmdb.org/t/p/w500/{}"

log = logging.getLogger(__name__)


class TMDBInfoProvider(object):
    name = "tmdb"

    def __init__(self, config):
        self.api_key = config["api_key"]
        self.session = requests.Session()
        self.session.params["api_key"] = self.api_key

    def get(self, url, *args, **kwargs):
        r = self.session.get(BASE_URL + url, *args, **kwargs)
        r.raise_for_status()

        if int(r.headers.get("X-RateLimit-Remaining", 0)) <= 1:
            backoff = int(r.headers.get("X-RateLimit-Reset")) - time.time()
            log.warning(
                "Hit TMDB ratelimit, waiting until %s (%ss)",
                r.headers.get("X-RateLimit-Reset"),
                backoff + 1,
            )
            time.sleep(backoff + 1)

        return r.json()

    def cast_series(self, obj, with_network=True, with_external_ids=False):
        provider_ids = {"tmdb": obj["id"]}
        if with_external_ids:
            external_ids = self.get("tv/{}/external_ids".format(obj["id"]))
            if "imdb_id" in external_ids:
                provider_ids["imdb"] = external_ids["imdb_id"]

        network = None
        if with_network:
            details = self.get("tv/{}".format(obj["id"]))
            if details["networks"]:
                network = details["networks"][0]["name"]

        series = SeriesMetadata(
            provider_ids=provider_ids,
            status=Series.AirStatus.UNKNOWN,
            name=obj["name"],
            desc=obj["overview"],
            network=network,
            content_rating=None,
            banner=IMAGE_URL_FORMAT.format(obj["backdrop_path"]),
            poster=IMAGE_URL_FORMAT.format(obj["poster_path"]),
        )

        return series

    def cast_season(self, obj):
        return SeasonMetadata(
            number=str(obj["season_number"]), episode_count=obj["episode_count"]
        )

    def cast_episode(self, obj):
        return EpisodeMetadata(
            number=str(obj["episode_number"]),
            name=obj["name"],
            desc=obj["overview"],
            airdate=obj["air_date"],
            imdb_id=None,
        )

    def search_series(self, name, **kwargs):
        obj = self.get("search/tv", params={"query": name})
        return [self.cast_series(series, **kwargs) for series in obj["results"]]

    def find_by_external(self, provider_ids):
        return None

    def get_series(self, id):
        return self.cast_series(self.get("tv/{}".format(id)), with_external_ids=True)

    def get_seasons(self, id):
        obj = self.get("tv/{}".format(id))
        return [self.cast_season(season) for season in obj["seasons"]]

    def get_episodes(self, id, season):
        obj = self.get("tv/{}/season/{}".format(id, season))
        return [self.cast_episode(episode) for episode in obj["episodes"]]
