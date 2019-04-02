from peewee import *

from bard.models import BaseModel
from bard.models.episode import Episode


@BaseModel.register
class Torrent(BaseModel):
    class State:
        NONE = 0
        DOWNLOADING = 1
        SEEDING = 2
        COMPLETED = 3

        ALL = {NONE, DOWNLOADING, SEEDING, COMPLETED}

    download_provider_id = CharField(null=True)
    fetch_provider_id = CharField(null=True)
    episode = ForeignKeyField(Episode, related_name='torrents', on_delete='CASCADE')
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
    def from_result(cls, episode, torrent, raw):
        return cls.create(
            episode=episode,
            title=torrent.title,
            fetch_provider_id=torrent.id,
            size=torrent.size,
            seeders=torrent.seeders,
            leechers=torrent.leechers,
            raw=raw)

    @property
    def state_readable(self):
        for k in dir(self.State):
            if getattr(self.State, k) == self.state:
                return k.title()
        return None
