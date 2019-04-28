import requests
import logging


class BaseDownloadProvider(object):
    def __init__(self, opts):
        self.__dict__.update(opts)
        self.log = logging.getLogger(self.__class__.__name__)

    def search(self, episode):
        raise NotImplementedError(
            '{} must override BaseDownloadProvider.search'.format(self.__class__.__name__))


class HTTPSessionProviderMixin(object):
    @property
    def session(self):
        if not hasattr(self, '_session'):
            self.create_session()
        return self._session

    def create_session(self):
        self._session = requests.Session()
        self.login()

    def login(self):
        raise NotImplementedError(
            '{} must override HTTPSessionProviderMixin.login'.format(self.__class__.__name__))
