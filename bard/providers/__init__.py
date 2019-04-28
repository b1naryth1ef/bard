import sys
import logging

log = logging.getLogger(__name__)


def get_provider_from_config(provider_type, provider_config):
    try:
        module_name = 'bard.providers.{}'.format(provider_type)
        __import__(module_name)
        registered_providers = sys.modules[module_name].PROVIDERS
    except Exception:
        log.exception('Failed to load provider type %s: ', provider_type)
        raise

    if provider_config['name'] not in registered_providers:
        raise Exception('Invalid Provider {}: unknown provider type {}'.format(
            provider_type, provider_config['name']
        ))

    return registered_providers[provider_config['name']](provider_config)


class DownloadAggregator(object):
    def __init__(self, config):
        self._config = config
        self._providers = {}

        for source in config.get('sources', []):
            if source['name'] in self._providers:
                raise Exception('Duplicate provider {}'.format(source['name']))

            self._providers[source['name']] = get_provider_from_config('download', source)

    def _get(self, provider_name):
        if provider_name not in self._providers:
            raise Exception('Referenced provider hasn\'t been configured as a source: {}'.format(provider_name))

        return self._providers[provider_name]

    @property
    def default(self):
        return self._config['default']

    def search(self, episode):
        provider = self._get(episode.series.download_provider or self._config['default'])
        return provider.search(episode)

    def get_torrent(self, torrent_id, provider):
        return self._get(provider).get_torrent(torrent_id)

    def get_torrent_contents(self, metadata):
        provider = self._get(metadata.provider)
        return provider.get_torrent_contents(metadata.provider_id)


class Providers(object):
    def load_from_config(self, config):
        from bard.util.info import InfoAggregator

        self.download = DownloadAggregator(config['providers']['download'])
        self.fetch = get_provider_from_config('fetch', config['providers']['fetch']['source'])
        self.info = InfoAggregator(config['providers']['info'])
        self.library = get_provider_from_config('library', config['providers']['library']['source'])
        self.notify = get_provider_from_config('notify', config['providers']['notify']['source'])


providers = Providers()
