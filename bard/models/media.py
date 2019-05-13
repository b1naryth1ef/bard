from collections import namedtuple

from peewee import ForeignKeyField, CharField, IntegerField

from bard.models import BaseModel
from bard.models.episode import Episode


MediaMetadata = namedtuple('MediaMetadata', (
    'season_number',
    'episode_number',
    'library_id',
    'video_codec',
    'audio_codec',
    'width',
    'height',
    'duration',
    'bitrate',
    'path',
    'size',
))


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

    @classmethod
    def from_metadata(cls, episode, metadata):
        return cls.create(
            episode=episode,
            library_id=metadata.library_id,
            video_codec=metadata.video_codec,
            audio_codec=metadata.audio_codec,
            width=metadata.width,
            height=metadata.height,
            duration=metadata.duration,
            bitrate=metadata.bitrate,
            path=metadata.path,
            size=metadata.size,
        )

    def __repr__(self):
        return u'<Media {}>'.format(self.id)

    def update_from_metadata(self, metadata):
        self.video_codec = metadata.video_codec
        self.audio_codec = metadata.audio_codec
        self.width = metadata.width
        self.height = metadata.height
        self.duration = metadata.duration
        self.bitrate = metadata.bitrate
        self.path = metadata.path
        self.size = metadata.size
