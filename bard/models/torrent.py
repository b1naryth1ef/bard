from datetime import datetime, timedelta
from collections import namedtuple

from peewee import (
    CharField,
    ForeignKeyField,
    IntegerField,
    BooleanField,
    BlobField,
    DateTimeField,
)

from bard.app import config
from bard.providers import providers
from bard.models import BaseModel
from bard.models.episode import Episode


TorrentMetadata = namedtuple(
    "TorrentMetadata",
    ("provider", "provider_id", "title", "size", "seeders", "leechers"),
)


@BaseModel.register
class Torrent(BaseModel):
    class State:
        NONE = 0
        DOWNLOADING = 1
        SEEDING = 2
        COMPLETED = 3

        ALL = {NONE, DOWNLOADING, SEEDING, COMPLETED}

    download_provider = CharField(null=True)
    download_provider_id = CharField(null=True)

    fetch_provider_id = CharField(null=True)
    episode = ForeignKeyField(Episode, backref="torrents", on_delete="CASCADE")
    state = IntegerField(default=State.NONE, choices=State.ALL)

    # Whether this torrent was post-processed
    processed = BooleanField(default=False)

    # Torrent metadata (not updated from fetch provider)
    title = CharField()
    size = CharField()
    seeders = IntegerField()
    leechers = IntegerField()
    raw = BlobField()

    # Date this torrent finished downloading (used for cleanup)
    done_date = DateTimeField(null=True)

    @classmethod
    def from_metadata(cls, episode, metadata, raw):
        return cls.create(
            download_provider=metadata.provider,
            download_provider_id=metadata.provider_id,
            episode=episode,
            title=metadata.title,
            size=metadata.size,
            seeders=metadata.seeders,
            leechers=metadata.leechers,
            raw=raw,
        )

    @property
    def state_readable(self):
        for k in dir(self.State):
            if getattr(self.State, k) == self.state:
                return k.title()
        return None

    @property
    def seeding_days_left(self):
        if (
            not config["seed_days"]
            or not self.done_date
            or self.state == Torrent.State.COMPLETED
        ):
            return 0

        done_at = self.done_date + timedelta(days=config["seed_days"])
        if done_at < datetime.utcnow():
            return 0

        return (done_at - datetime.utcnow()).days

    def remove(self):
        providers.fetch.remove(self)
        self.delete_instance()
