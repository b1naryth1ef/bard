try:
    import urlparse
except ImportError:
    from urllib import parse as urlparse
from peewee import Model, Proxy
from playhouse.sqlite_ext import SqliteExtDatabase, JSONField


__all__ = [
    'JSONField',
    'BaseModel',
    'database',
    'REGISTERED_MODELS',
    'init_db',
]


REGISTERED_MODELS = []

# Create a database proxy we can setup post-init
database = Proxy()


class BaseModel(Model):
    class Meta:
        database = database

    @staticmethod
    def register(cls):
        REGISTERED_MODELS.append(cls)
        return cls

    @classmethod
    def with_id(cls, oid, *fields):
        try:
            return cls.select(*fields).get(oid)
        except cls.DoesNotExist:
            return None


def init_db(config):
    # TODO: dynamic
    import bard.models.episode
    import bard.models.season
    import bard.models.series
    import bard.models.torrent
    import bard.models.media

    obj = urlparse.urlparse(config['database'])

    if obj.scheme == "sqlite":
        database.initialize(SqliteExtDatabase(obj.netloc, pragmas=[
            ('foreign_keys', 1)
        ], check_same_thread=False))
    else:
        raise Exception('Unsupported database adapter `{}`, for DB url `{}`'.format(obj.scheme, config['database']))

    for model in REGISTERED_MODELS:
        model.create_table(True)
