from peewee import *

from bard.models import BaseModel
from bard.models.episode import Episode


@BaseModel.register
class Media(BaseModel):
    episode = ForeignKeyField(Episode, backref='medias', on_delete='CASCADE')

    library_id = CharField(unique=True)

    video_codec = CharField(null=True)
    audio_codec = CharField(null=True)
    width = IntegerField()
    height = IntegerField()
    duration = IntegerField()
    bitrate = IntegerField()

    path = CharField(null=True)
    size = IntegerField(null=True)

    def __repr__(self):
        return u'<Media %s>'.format(self.id)
