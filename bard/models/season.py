from collections import namedtuple
from peewee import *
from bard.models import BaseModel
from bard.models.series import Series


SeasonMetadata = namedtuple('SeasonMetadata', (
    'number',
    'episode_count',
))


@BaseModel.register
class Season(BaseModel):
    class Meta:
        indexes = (
            (('series', 'number'), True),
        )

    series = ForeignKeyField(Series, backref='seasons', on_delete='CASCADE')

    number = CharField()
    episode_count = IntegerField()

    # Do we want upcoming epsidoes of this show to auto-subscribe?
    subscribed = BooleanField(default=False)

    @classmethod
    def from_metadata(cls, series, metadata):
        return cls.create(
            series=series,
            number=metadata.number,
            episode_count=metadata.episode_count,
        )

    def update_from_metadata(self, metadata):
        self.episode_count = metadata.episode_count
