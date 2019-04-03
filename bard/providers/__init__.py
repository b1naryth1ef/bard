import sys
import logging

log = logging.getLogger(__name__)


class Providers(object):
    def load_from_config(self, config):
        for provider_type, provider_config in config['providers'].items():
            try:
                module_name = 'bard.providers.{}'.format(provider_type)
                __import__(module_name)
                registered_providers = sys.modules[module_name].PROVIDERS
            except Exception:
                log.exception('Failed to load provider type %s: ', provider_type)
                continue

            if provider_config['name'] not in registered_providers:
                raise Exception('Invalid Provider {}: unknown provider type {}'.format(
                    provider_type, provider_config['name']
                ))

            setattr(self, provider_type, registered_providers[provider_config['name']](provider_config))


providers = Providers()
