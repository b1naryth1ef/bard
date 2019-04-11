import string
from datetime import datetime
from collections import namedtuple
from peewee import *
from bard.models import BaseModel, JSONField


SeriesMetadata = namedtuple('SeriesMetadata', (
    'provider_ids',
    'status',
    'name',
    'desc',
    'network',
    'content_rating',
    'banner',
    'poster',
    'imdb_id',
))


@BaseModel.register
class Series(BaseModel):
    class Meta:
        indexes = (
            (('name', ), True),
        )

    class AirStatus:
        UNKNOWN = 1
        UPCOMING = 2
        CONTINUING = 3
        ENDED = 4

        ALL = {UNKNOWN, UPCOMING, CONTINUING, ENDED}

    # Basic info
    name = CharField()
    storage_name_override = CharField(null=True)
    desc = CharField(null=True)
    network = CharField(null=True)
    content_rating = CharField(null=True)

    # Show status
    status = IntegerField(default=AirStatus.UNKNOWN, choices=AirStatus.ALL)

    # Do we want upcoming seasons of this show to auto-subscribe?
    subscribed = BooleanField(default=False)

    # Images
    banner = CharField(null=True)
    poster = CharField(null=True)

    # Metadata
    imdb_id = CharField(null=True)

    # Metadata
    added_date = DateTimeField(default=datetime.utcnow)

    provider_ids = JSONField()

    @property
    def clean_name(self):
        return ''.join([c for c in self.name if c in string.ascii_letters + ' '])

    @property
    def storage_name(self):
        if self.storage_name_override:
            return self.storage_name_override
        return self.name.replace('.', '').replace(' ', '.').replace('-', '.')

    @classmethod
    def from_metadata(cls, metadata):
        return cls.create(
            provider_ids=metadata.provider_ids,
            status=metadata.status,
            name=metadata.name,
            desc=metadata.desc,
            network=metadata.network,
            content_rating=metadata.content_rating,
            banner=metadata.banner,
            poster=metadata.poster,
            imdb_id=metadata.imdb_id,
        )

    def get_provider_id(self, provider_name):
        try:
            return self.provider_ids[provider_name]
        except KeyError:
            raise Exception('No provider ID for series {} provider {}'.format(
                self.id,
                provider_name,
            ))

    def update_from_metadata(self, metadata):
        self.status = metadata.status
        self.name = metadata.name
        self.desc = metadata.desc
        self.network = metadata.network
        self.content_rating = metadata.content_rating
        self.banner = metadata.banner
        self.poster = metadata.poster
        self.imdb_id = metadata.imdb_id
