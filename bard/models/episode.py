from collections import namedtuple
from datetime import datetime

from peewee import ForeignKeyField, IntegerField, CharField, DateTimeField

from bard.constants import QUALITIES
from bard.models import BaseModel
from bard.models.season import Season
from bard.providers import providers


EpisodeMetadata = namedtuple('EpisodeMetadata', (
    'number',
    'name',
    'desc',
    'airdate',
    'imdb_id',
))


@BaseModel.register
class Episode(BaseModel):
    class Meta:
        indexes = (
            (('season', 'number'), True),
        )

    class State:
        NONE = 0
        WANTED = 1
        FETCHED = 2
        DOWNLOADED = 3

        ALL = {NONE, WANTED, FETCHED, DOWNLOADED}

    season = ForeignKeyField(Season, backref='episodes', on_delete='CASCADE')
    state = IntegerField(default=State.NONE, choices=State.ALL)

    number = CharField()
    name = CharField(null=True)
    desc = CharField(null=True)
    airdate = DateTimeField(null=True)

    # Metadata
    imdb_id = CharField(null=True)

    # Quality Preference
    quality = CharField(default='', choices=QUALITIES, null=True)

    @property
    def aired(self):
        if self.airdate:
            return self.airdate < datetime.utcnow()
        return False

    @property
    def series(self):
        return self.season.series if self.season else None

    @property
    def season_episode_id(self):
        return 'S{}E{}'.format(self.season.number, self.number)

    @classmethod
    def from_metadata(cls, season, metadata, state=0):
        return cls.create(
            season=season,
            state=state,
            number=metadata.number,
            name=metadata.name,
            desc=metadata.desc,
            airdate=metadata.airdate,
            imdb_id=metadata.imdb_id
        )

    def update_from_metadata(self, metadata):
        self.name = metadata.name
        self.desc = metadata.desc
        self.airdate = metadata.airdate
        self.imdb_id = metadata.imdb_id

    def fetch(self, torrent_metadata):
        from bard.models.torrent import Torrent

        raw = providers.download.get_torrent_contents(torrent_metadata.id)

        torrent = Torrent.from_result(self, torrent_metadata, raw)
        torrent.fetch_provider_id = providers.fetch.download(torrent)
        torrent.state = torrent.State.DOWNLOADING
        torrent.save()

        self.state = self.State.FETCHED
        self.save()

    def to_string(self):
        return '{} - {}'.format(self.series.name, self.season_episode_id)

    def __repr__(self):
        return '<Episode - S{}E{} ({})>'.format(
            self.season.number if self.season else '??',
            self.number,
            self.series.name if self.series else '??',
        )

    @staticmethod
    def sanitize_name(name):
        return name.replace("'", '').replace('.', '_')

    def generate_search_queries(self):
        series_name = self.series.name.replace("'", '')

        fmt = '{} S{}E{} {}'.format(
            series_name,
            self.season.number.zfill(2),
            self.number.zfill(2),
            '{}')

        queries = []

        # Iterate over qualities in the order we want
        qualities = list(QUALITIES)

        # If we have a preferred quality, order it first
        if self.quality:
            qualities.remove(self.quality)
            qualities = [self.quality] + qualities

        for quality in qualities:
            # First, generate our preferred qualities
            queries.append(fmt.format(quality))

        # TODO: as a fallback, we should search for the entire season
        return queries
