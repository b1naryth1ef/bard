import pytest

from bard.providers.download.horriblesubs import HorribleSubsDownloadProvider


class FakeSeries(object):
    def __init__(self, name):
        self.name = name


class FakeSeason(object):
    def __init__(self, series, number):
        self.series = series
        self.number = number


class FakeEpisode(object):
    def __init__(self, season, number, quality=None):
        self.season = season
        self.series = season.series
        self.number = number
        self.quality = quality


@pytest.fixture(scope="function")
def horriblesubs():
    return HorribleSubsDownloadProvider({})


def test_search(horriblesubs):
    series = FakeSeries("one punch man")
    season = FakeSeason(series, "1")
    episode = FakeEpisode(season, "5")

    results = horriblesubs.search(episode)
    assert len(results) == 3
    assert {i.title for i in results} == {"480p", "720p", "1080p"}


def test_get_torrent_contents(horriblesubs):
    result = horriblesubs.get_torrent_contents("351-05-720p")
    assert b"S42OV4WLCTATYOVBDBPKL5YKO57TNOUN" in result
