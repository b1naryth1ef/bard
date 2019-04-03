import re

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
