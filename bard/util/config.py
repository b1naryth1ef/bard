import os
import yaml


class ConfigurationException(Exception):
    pass


class Configuration(object):
    def __init__(self, locations, validations=None):
        self._locations = locations
        self._validations = validations or {}
        self._data = {}
        self.load()

    def load(self):
        for location in self._locations:
            path = os.path.join(location, 'bard.yaml')
            if os.path.exists(path):
                break
        else:
            raise ConfigurationException('Failed to find configuration (paths: {})'.format(
                ' '.join(self._locations)
            ))

        with open(path, 'r') as f:
            self._data = yaml.load(f.read(), Loader=yaml.SafeLoader)

    def __getitem__(self, name):
        return self._data[name]

    def get(self, name, default=None):
        parts = name.split('.')

        try:
            cur = self._data
            for part in parts:
                cur = cur[part]
        except KeyError:
            return default

        return cur

    def _validate(self):
        for path, value in self._validations.items():
            data = self.get(path)
            if data is None:
                raise ConfigurationException('Required value `{}` unset in configuration'.format(
                    path,
                ))

            if value is not None:
                if not isinstance(data, value):
                    raise ConfigurationException('Invalid type for value `{}` is {} should be {}'.format(
                        path,
                        type(data),
                        value,
                    ))
