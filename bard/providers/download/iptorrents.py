import re
import cfscrape

try:
    from urllib import urlencode
except ImportError:
    from urllib.parse import urlencode

from pyquery import PyQuery
from .base import BaseDownloadProvider, HTTPSessionProviderMixin
from bard.models.torrent import TorrentMetadata


ID_RE = re.compile(r"\?id=(\d+)")
PEERS_RE = re.compile(r"(\d)+ seeders \+ (\d+) leechers")


class IPTorrentsDownloadProvider(BaseDownloadProvider, HTTPSessionProviderMixin):
    PARAMS = {"username", "password"}

    URLS = {
        "BASE": "https://iptorrents.eu",
        "LOGIN": "/take_login.php",
        "SEARCH": "/t",
        "DOWNLOAD": "/download.php",
        "INFO": "/details.php?id={}",
    }

    def login(self):
        self.cookies, self.ua = cfscrape.get_tokens(
            url="https://iptorrents.eu/login.php"
        )
        r = self.session.get(
            self.URLS["BASE"] + self.URLS["LOGIN"],
            params={"username": self.username, "password": self.password},
            headers={"User-Agent": self.ua},
            cookies=self.cookies,
        )
        r.raise_for_status()

        # TODO: validation for common errors

    def search(self, episode, exclude=None):
        query = "{} S{}E{}".format(
            episode.series.search_name.replace("'", ""),
            episode.season.number.zfill(2),
            episode.number.zfill(2),
        )

        r = self.session.get(
            self.URLS["BASE"] + self.URLS["SEARCH"],
            params=urlencode({"q": query}) + ";o=seeders",
            headers={"User-Agent": self.ua},
            cookies=self.cookies,
        )

        r.raise_for_status()

        torrents = list(self._parse_search_results(r.content, exclude=exclude))
        if not len(torrents):
            return []

        return torrents

    def get_torrent_contents(self, torrent_id):
        r = self.session.get(
            self.URLS["BASE"]
            + self.URLS["DOWNLOAD"]
            + "/{0}/{0}.torrent".format(torrent_id),
            headers={"User-Agent": self.ua},
            cookies=self.cookies,
        )
        r.raise_for_status()
        return r.content

    def _parse_torrent(self, torrent_id, raw):
        if "No torrent with this id." in raw:
            return None

        q = PyQuery(raw)

        seeders, leechers = re.findall(PEERS_RE, q(".vat")[1].text)[0]

        return TorrentMetadata(
            provider="iptorrents",
            provider_id=torrent_id,
            title=next(q(".td_fname")[0].iterchildren()).text.strip(),
            size=q(".vat")[3].text.split(" ")[0],
            seeders=seeders,
            leechers=leechers,
        )

    def _parse_search_results(self, raw, exclude=None):
        q = PyQuery(raw)

        # Grab all table rows in the torrents section
        torrents = q("#torrents")("tr")

        # Won't be any if the search failed
        if not len(torrents):
            return []

        # Otherwise, skip the first row (its the header)
        torrents = torrents[1:]

        # No torrents found
        if len(list(torrents[-1].iterchildren())) == 1:
            return []

        results = []
        for torrent in torrents:
            parts = list(torrent.iterchildren())

            id = re.findall(ID_RE, next(parts[1].iterchildren()).attrib["href"])[0]
            if exclude and id in exclude:
                continue

            title = list(parts[1].iterchildren())[0].text_content()

            # TODO: convert
            size = parts[5].text_content()

            # Grab S/L
            seeders = int(parts[7].text_content())
            leechers = int(parts[8].text_content())

            results.append(
                TorrentMetadata("iptorrents", id, title, size, seeders, leechers)
            )

        return results
