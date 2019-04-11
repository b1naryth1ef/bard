from peewee import *
from bard.models import BaseModel
from bard.models.series import Series


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

    def merge(self, other):
        self.episode_count = other.episode_count
