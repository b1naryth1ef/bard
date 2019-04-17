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


class Providers(object):
    def load_from_config(self, config):
        from bard.util.info import InfoAggregator

        for provider_type, provider_config in config['providers'].items():
            setattr(self, provider_type, get_provider_from_config(provider_type, provider_config))

        self.info = InfoAggregator(config['info'])


providers = Providers()
