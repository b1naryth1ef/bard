import re
import urllib

from pyquery import PyQuery
from .base import BaseDownloadProvider, HTTPSessionProviderMixin, TorrentMetadata

ID_RE = re.compile(r'\?id=(\d+)')
PEERS_RE = re.compile(r'(\d)+ seeders \+ (\d+) leechers')


class IPTorrentsDownloadProvider(BaseDownloadProvider, HTTPSessionProviderMixin):
    PARAMS = {
        'username',
        'password',
    }

    URLS = {
        'BASE': 'https://iptorrents.com',
        'LOGIN': '/take_login.php',
        'SEARCH': '/t',
        'DOWNLOAD': '/download.php',
        'INFO': '/details.php?id={}',
    }

    def login(self):
        r = self.session.get(self.URLS['BASE'] + self.URLS['LOGIN'], params={
            'username': self.username,
            'password': self.password,
        })
        r.raise_for_status()

        # TODO: validation for common errors

    def search(self, episode, exclude=None):
        queries = episode.generate_search_queries()

        if not len(queries):
            raise Exception('nothing to search')

        for query in queries:
            # query = urllib.encode(query) #+ ';o=seeders')
            r = self.session.get(self.URLS['BASE'] + self.URLS['SEARCH'],
                params=urllib.urlencode({
                    'q': query
                }) + ';o=seeders')

            r.raise_for_status()

            torrents = list(self._parse_search_results(r.content, exclude=exclude))
            if not len(torrents):
                continue

            # Determine whether a match is good or not first
            return torrents

        return []

    def get_torrent(self, torrent_id):
        r = self.session.get(self.URLS['BASE'] + self.URLS['INFO'].format(torrent_id))
        r.raise_for_status()
        return self._parse_torrent(torrent_id, r.content)

    def get_torrent_contents(self, torrent_id):
        r = self.session.get(
            self.URLS['BASE'] + self.URLS['DOWNLOAD'] + '/{0}/{0}.torrent'.format(torrent_id))
        r.raise_for_status()
        return r.content

    def _parse_torrent(self, torrent_id, raw):
        if 'No torrent with this id.' in raw:
            return None

        q = PyQuery(raw)

        seeders, leechers = re.findall(PEERS_RE, q('.vat')[1].text)[0]

        return TorrentMetadata(
            torrent_id,
            next(q('.td_fname')[0].iterchildren()).text.strip(),
            q('.vat')[3].text.split(' ')[0],
            seeders,
            leechers
        )

    def _parse_search_results(self, raw, exclude=None):
        q = PyQuery(raw)

        # Grab all table rows in the torrents section
        torrents = q("#torrents")("tr")

        # Won't be any if the search failed
        if not len(torrents):
            raise StopIteration

        # Otherwise, skip the first row (its the header)
        torrents = torrents[1:]

        # No torrents found
        if len(list(torrents[-1].iterchildren())) == 1:
            raise StopIteration

        for torrent in torrents:
            parts = list(torrent.iterchildren())

            id = re.findall(ID_RE, next(parts[1].iterchildren()).attrib['href'])[0]
            if exclude and id in exclude:
                continue

            title = list(parts[1].iterchildren())[0].text_content()

            # TODO: convert
            size = parts[5].text_content()

            # Grab S/L
            seeders = int(parts[7].text_content())
            leechers = int(parts[8].text_content())

            yield TorrentMetadata(id, title, size, seeders, leechers)
