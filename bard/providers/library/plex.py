from plexapi.server import PlexServer
from plexapi.exceptions import NotFound
from bard.models.media import Media
from collections import defaultdict


class PlexLibraryProvider(object):
    def __init__(self, bard, config):
        self.config = config
        self.plex = PlexServer(config['url'], config['token'])

    @property
    def section(self):
        return self.plex.library.section(self.config.get('section', 'TV Shows'))

    def get_all_series(self):
        return [show.title for show in self.section.all()]

    def find_series_media(self, series_name):
        seasons = defaultdict(dict)

        r = self.section.get(series_name)
        for episode in r.episodes():
            medias = []
            for media in episode.media:
                assert len(media.parts) == 1
                medias.append(Media(
                    library_id=media.id,
                    video_codec=media.videoCodec,
                    audio_codec=media.audioCodec,
                    width=media.width,
                    height=media.height,
                    duration=media.duration,
                    bitrate=media.bitrate,
                    path=media.parts[0].file,
                ))
            seasons[episode.seasonNumber][episode.index] = medias
        return seasons

    def find_series_info(self, series_name):
        try:
            r = self.section.get(series_name)
        except NotFound:
            return None

        return {
            'title': r.title,
            'content_rating': r.contentRating,
            'guid': r.guid,
        }

    def search_series(self, query):
        return self.section.searchShows(title=query)
