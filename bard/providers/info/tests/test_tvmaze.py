from datetime import datetime

import pytest
from bard.providers.info.tvmaze import TVMazeInfoProvider


@pytest.fixture(scope='function')
def tvmaze():
    return TVMazeInfoProvider({})


def test_raw_api_call(tvmaze):
    data = tvmaze.get('search/shows', params={
        'q': 'Heavy Rescue',
    })

    assert len(data) == 1
    assert data[0]['show']['name'] == 'Heavy Rescue: 401'


def test_search_series(tvmaze):
    results = tvmaze.search_series('one punch man')

    assert len(results) == 1
    assert results[0].provider_id == 4201
    assert results[0].name == 'One-Punch Man'
    assert results[0].imdb_id == 'tt4508902'


def test_get_series(tvmaze):
    series = tvmaze.get_series(99)

    assert series.provider_id == 99
    assert series.name == "America's Next Top Model"
    assert series.imdb_id == 'tt0363307'


def test_get_seasons(tvmaze):
    seasons = tvmaze.get_seasons(150)
    assert seasons[0].number == '1'
    assert seasons[0].episode_count == 12


def test_get_episodes(tvmaze):
    episodes = tvmaze.get_episodes(150, 1)
    assert len(episodes) == 12
    assert episodes[0].name == 'Pilot'
    assert episodes[0].number == '1'
    assert episodes[0].airdate == datetime(2011, 1, 10, 3, 0)
