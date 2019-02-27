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

    episode = ForeignKeyField(Episode, related_name='torrents', on_delete='CASCADE')
    uid = CharField(null=True)
    state = IntegerField(default=State.NONE, choices=State.ALL)

    processed = BooleanField(default=False)

    title = CharField()
    provider_id = CharField()
    size = CharField()
    seeders = IntegerField()
    leechers = IntegerField()

    raw = BlobField()

    @classmethod
    def from_result(cls, episode, torrent, raw):
        return cls.create(
            episode=episode,
            title=torrent.title,
            provider_id=torrent.id,
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
