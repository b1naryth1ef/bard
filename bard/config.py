import os
import json
import copy


DEFAULT_CONFIG = {
    'database': 'sqlite://bard.db',
    'default_quality': '1080p',
    'providers': {
        'info': {'name': 'tvdb'},
        'download': {},
        'fetch': {},
    },
    'directories': {
        'input': None,
        'output': None,
        'temporary': None,
    },
    'seed_days': 16,
    'web': {
        'host': '',
        'port': 7675,
        'user_header': 'X-Forwarded-User',
        'secret_key': '',
    },
    'acls': {}
}


class BardConfig(object):
    def __init__(self, path):
        self._path = path

    def get(self, key, default):
        return getattr(self, key, default)

    @classmethod
    def load(cls, path='config.json'):
        self = cls(path)

        if not os.path.exists(path):
            self.dump()

        with open(path, 'r') as f:
            obj = copy.deepcopy(DEFAULT_CONFIG)
            obj.update(json.load(f))
            return obj

    def dump(self):
        obj = {k: v for k, v in self.__dict__.items() if not k.startswith('_')}

        with open(self._path, 'w') as f:
            json.dump(obj, f)
