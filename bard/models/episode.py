from collections import namedtuple
from datetime import datetime

from peewee import ForeignKeyField, IntegerField, CharField, DateTimeField

from bard.models import BaseModel, database
from bard.models.season import Season
from bard.providers import providers


EpisodeMetadata = namedtuple(
    "EpisodeMetadata", ("number", "name", "desc", "airdate", "imdb_id")
)


@BaseModel.register
class Episode(BaseModel):
    class Meta:
        indexes = ((("season", "number"), True),)

    class State:
        NONE = 0
        WANTED = 1
        FETCHED = 2
        DOWNLOADED = 3

        ALL = {NONE, WANTED, FETCHED, DOWNLOADED}

    season = ForeignKeyField(Season, backref="episodes", on_delete="CASCADE")
    state = IntegerField(default=State.NONE, choices=State.ALL)

    number = CharField()
    name = CharField(null=True)
    desc = CharField(null=True)
    airdate = DateTimeField(null=True)

    # Metadata
    imdb_id = CharField(null=True)

    # Quality Preference
    quality = CharField(default="", null=True)

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
        return "S{}E{}".format(self.season.number, self.number)

    @classmethod
    def from_metadata(cls, season, metadata, state=0):
        return cls.create(
            season=season,
            state=state,
            number=metadata.number,
            name=metadata.name,
            desc=metadata.desc,
            airdate=metadata.airdate,
            imdb_id=metadata.imdb_id,
        )

    def update_from_metadata(self, metadata):
        self.name = metadata.name
        self.desc = metadata.desc
        self.airdate = metadata.airdate
        self.imdb_id = metadata.imdb_id

    def fetch(self, torrent_metadata):
        from bard.models.torrent import Torrent

        raw = providers.download.get_torrent_contents(torrent_metadata)

        # If our upstream fetch provider has an error when downloading this could
        #  leave unused torrent records sitting around the database despite the
        #  episode remaining in WANTED. We atomic to ensure the row creation within
        #  `from_metadata` is reverted if the upstream fetch provider has an error.
        # TODO: `Torrent.from_metadata` should just return a unsaved Torrent object
        #  so we can avoid this and related sheneigans inside of
        #  views/episode.py:episode_fetch_direct
        with database.atomic():
            torrent = Torrent.from_metadata(self, torrent_metadata, raw)
            self.fetch_torrent(torrent)

    def fetch_torrent(self, torrent):
        torrent.fetch_provider_id = providers.fetch.download(torrent)
        torrent.state = torrent.State.DOWNLOADING
        torrent.save()

        # Only mark as FETCHED if we don't have local media assets
        if self.state != self.State.DOWNLOADED:
            self.state = self.State.FETCHED
            self.save()

    def to_string(self):
        return "{} - {}".format(self.series.name, self.season_episode_id)

    def __repr__(self):
        return "<Episode - S{}E{} ({})>".format(
            self.season.number if self.season else "??",
            self.number,
            self.series.name if self.series else "??",
        )

    @staticmethod
    def sanitize_name(name):
        return name.replace("'", "").replace(".", "_")
