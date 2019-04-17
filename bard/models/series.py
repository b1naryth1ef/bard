import string
from datetime import datetime

from peewee import *
from bard.models import BaseModel


@BaseModel.register
class Series(BaseModel):
    class Meta:
        indexes = (
            (('provider_id', 'name'), True),
        )

    class AirStatus:
        UNKNOWN = 1
        UPCOMING = 2
        CONTINUING = 3
        ENDED = 4

        ALL = {UNKNOWN, UPCOMING, CONTINUING, ENDED}

    # Used to track this series under a provider
    provider_id = IntegerField()

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

    @property
    def clean_name(self):
        return ''.join([c for c in self.name if c in string.ascii_letters + ' '])

    @property
    def storage_name(self):
        if self.storage_name_override:
            return self.storage_name_override
        return self.name.replace('.', '').replace(' ', '.').replace('-', '.')
