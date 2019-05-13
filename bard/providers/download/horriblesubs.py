import re

import requests
from pyquery import PyQuery

from bard.models.torrent import TorrentMetadata

BASE_URL = "https://horriblesubs.info/"
API_URL = BASE_URL + "api.php"
SHOW_ID_RE = re.compile(r"var hs_showid = (\d+);")


class HorribleSubsDownloadProvider(object):
    def __init__(self, config):
        self._session = requests.Session()

    def _metadata_for_rls_link(self, show_id, link):
        return TorrentMetadata(
            provider="horriblesubs",
            provider_id="{}-{}".format(show_id, link.attrib["id"]),
            title=link.cssselect(".rls-link-label")[0].text.strip()[:-1],
            size=0,
            seeders=0,
            leechers=0,
        )

    def _rls_links_for_episode(self, show_id, episode_id):
        r = self._session.get(
            API_URL, params={"method": "getshows", "type": "show", "showid": show_id}
        )
        r.raise_for_status()

        q = PyQuery(r.content)
        infos = q(".rls-info-container")

        for info in infos:
            if info.attrib["id"] != episode_id:
                continue

            links = info.cssselect(".rls-link")
            for link in links:
                yield link

    def search(self, episode):
        show_name = episode.series.name.replace(" ", "-")
        if episode.season.number != "1":
            show_name += "-s{}".format(episode.season.number)

        r = self._session.get(BASE_URL + "shows/{}/".format(show_name))
        if r.status_code == 404:
            return []
        r.raise_for_status()

        matches = SHOW_ID_RE.findall(r.content.decode("utf-8"))
        if not matches:
            return []

        results = []
        for link in self._rls_links_for_episode(matches[0], episode.number.zfill(2)):
            results.append(self._metadata_for_rls_link(matches[0], link))

        return results

    def get_torrent_contents(self, torrent_id):
        show_id, episode_id, res = torrent_id.split("-")

        for link in self._rls_links_for_episode(show_id, episode_id):
            if link.attrib["id"] != "{}-{}".format(episode_id, res):
                continue

            magnet_link = next(
                link.cssselect(".hs-magnet-link")[0].iterchildren(), None
            )
            return magnet_link.attrib["href"].encode("utf-8")

        return None
