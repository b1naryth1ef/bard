from datetime import date

import pytest
from bard.providers.info.tvdb import TVDBInfoProvider


@pytest.fixture(scope="function")
def tvdb():
    return TVDBInfoProvider({})


def test_search_series(tvdb):
    results = tvdb.search_series("one punch man")

    assert len(results) == 1
    assert results[0].provider_ids["tvdb"] == 293088
    assert results[0].provider_ids["imdb"] == "tt4508902"
    assert results[0].name == "One-Punch Man"


def test_get_series(tvdb):
    series = tvdb.get_series(71721)

    assert series.provider_ids["tvdb"] == 71721
    assert series.provider_ids["imdb"] == "tt0363307"
    assert series.name == "America's Next Top Model"


def test_get_seasons(tvdb):
    seasons = tvdb.get_seasons(161511)
    assert seasons[1].number == "1"
    assert seasons[1].episode_count == 12


def test_get_episodes(tvdb):
    episodes = tvdb.get_episodes(161511, 1)
    assert len(episodes) == 12
    assert episodes[0].name == "Pilot"
    assert episodes[0].number == "1"
    assert episodes[0].airdate == date(2011, 1, 9)
