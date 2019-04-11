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
        for provider_type, provider_config in config['providers'].items():
            setattr(self, provider_type, get_provider_from_config(provider_type, provider_config))

        self.info = InfoAggregator(config['info'])


def merge_named_tuple(a, b, fields):
    '''
    Merges all values of a into b, returning a new namedtuple.
    '''
    new_fields = set(fields)
    old_fields = set(a._fields) - new_fields

    values = []
    for field in a._fields:
        if field in old_fields:
            values.append(getattr(a, field))
        else:
            values.append(getattr(b, field))

    return a._make(values)


class InfoAggregator(object):
    def __init__(self, config):
        self._config = config
        self._providers = {}

        # Load any providers specified
        for provider in config.get('providers', []):
            if provider['name'] in self._providers:
                raise Exception('Duplicate Provider {}'.format(provider['name']))

            self._providers[provider['name']] = get_provider_from_config('info', provider)

    def search_series(self, name):
        provider = self._providers[self._config['search']]
        return provider.search_series(name)

    def _calculate_metadata(self, entity_type, func_name, series, *args):
        config = self._config['rules'][entity_type]

        # Load data for all providers that will be required in this merge
        provider_results = {}
        for provider in set(config.values()):
            if provider not in series.provider_ids:
                log.warning('Provider %s is not linked to season %s, skipping in aggregation', provider, series.id)
                continue

            provider_results[provider] = getattr(self._providers[provider], func_name)(
                series.provider_ids[provider],
                *args
            )

        # Generate a base metadata object
        base = provider_results[config['*']]
        if len(provider_results) == 1:
            return base

        if isinstance(base, list):
            provider_results = {
                k: {i.number: i for i in v} for k, v in provider_results.items()
            }

            new_items = {}
            for item in base:
                new_items[item.number] = item

                for provider, results in provider_results.items():
                    if item.number not in results:
                        continue
                    fields = [field for field, value in config.items() if value == provider and field != '*']
                    new_items[item.number] = merge_named_tuple(new_items[item.number], results[item.number], fields)

            base = list(new_items.values())
        else:
            for provider, result in provider_results.items():
                fields = [field for field, value in config.items() if value == provider and field != '*']
                base = merge_named_tuple(base, result, fields)

        return base

    def get_series_by_provider_id(self, provider_id):
        return self._providers[self._config['search']].get_series(provider_id)

    def get_series(self, series):
        return self._calculate_metadata('series', 'get_series', series)

    def get_seasons(self, series):
        return self._calculate_metadata('season', 'get_seasons', series)

    def get_episodes(self, series, season):
        return self._calculate_metadata('episode', 'get_episodes', series, season)

    def link_series_providers(self, series):
        need_save = False
        for provider_name, provider in self._providers.items():
            if provider_name in series.provider_ids:
                continue

            series_info = provider.find_by_external(series.provider_ids)
            if series_info:
                series.provider_ids.update(series_info.provider_ids)
                need_save = True
        return need_save


providers = Providers()
