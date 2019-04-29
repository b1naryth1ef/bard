import logging
import re

from bard.providers import get_provider_from_config

log = logging.getLogger(__name__)

YEAR_RE = re.compile(r'\(\d{4}\)')


def _sanitize_series_name(name):
    return re.sub(YEAR_RE, name, '').strip()


def select_best_series(info_provider, name):
    search_results = info_provider.search_series(name)
    for result in search_results:
        if result.name == name:
            return result

    vague_name = _sanitize_series_name(name)
    vague_search_results = info_provider.search_series(vague_name)
    for result in vague_search_results:
        if result.name == vague_name:
            return result

    return None


def merge_named_tuple(a, b, fields):
    """
    Merges all the provided field names in `fields` from b to a, returning a new
    namedtuple.
    """
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
    """
    Provides a unified interface for querying and compiling information and metadata
    about series, seasons, and episodes. This class implements the entire required
    interface for info providers, and thus is used in place of regular providers.
    """
    def __init__(self, config):
        self._config = config
        self._providers = {}

        # Load any providers specified
        for provider in config.get('sources', []):
            if provider['name'] in self._providers:
                raise Exception('Duplicate Provider {}'.format(provider['name']))

            self._providers[provider['name']] = get_provider_from_config('info', provider)

    def _calculate_metadata(self, entity_type, func_name, series, *args):
        """
        This function attempts to calculate a metadata object for a given entity
        type (series, season, episode). Internally this function queries information
        from all required providers (where required means that we'll use some or
        all of the returned metadata from that provider) and merges it together
        based on our configuration rules.

        :param str entity_type: the entity type (series, season, or episode)
        :param str func_name: the info method name to call
        :param Series series: the series this query is on
        """
        config = self._config['rules'][entity_type]

        providers_to_query = set(config.values())
        if not providers_to_query:
            providers_to_query = {self._config['default']}

        # Load data for all providers that will be required in this merge
        provider_results = {}
        for provider in providers_to_query:
            if provider not in series.provider_ids:
                log.warning('Provider %s is not linked to season %s, skipping in aggregation', provider, series.id)
                continue

            provider_results[provider] = getattr(self._providers[provider], func_name)(
                series.provider_ids[provider],
                *args
            )

        # Generate a base metadata object
        base_provider = config.get('*', self._config['default'])
        base = provider_results[base_provider]
        if len(provider_results) == 1:
            return base

        # If our result is a list we need to merge each individual result
        if isinstance(base, list):
            # We use the 'number' field as a UID for each entity
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

    def link_series_providers(self, series):
        """
        Attempts to link a series against all our configured providers. Internally
        this will query providers via `find_by_external` to merge in all possible
        provider_ids based on our configured providers.

        :return: bool
                 If any new providers where linked to this series. This can be
                 used to determine whether the caller must persist changes to
                 the provided series.
        """
        need_save = False
        for provider_name, provider in self._providers.items():
            if provider_name in series.provider_ids:
                continue

            series_info = provider.find_by_external(series.provider_ids)
            if series_info:
                series.provider_ids.update(series_info.provider_ids)
                need_save = True
        return need_save

    def search_series(self, name):
        provider = self._providers[self._config['default']]
        return provider.search_series(name)

    def get_series_by_provider_id(self, provider_id):
        return self._providers[self._config['default']].get_series(provider_id)

    def get_series(self, series):
        return self._calculate_metadata('series', 'get_series', series)

    def get_seasons(self, series):
        return self._calculate_metadata('season', 'get_seasons', series)

    def get_episodes(self, series, season):
        return self._calculate_metadata('episode', 'get_episodes', series, season)
