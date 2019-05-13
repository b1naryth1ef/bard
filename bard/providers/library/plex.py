from plexapi.server import PlexServer
from plexapi.exceptions import NotFound
from bard.models.media import MediaMetadata


class PlexLibraryProvider(object):
    def __init__(self, config):
        self.config = config
        self.plex = PlexServer(config["url"], config["token"])

    @property
    def _section(self):
        return self.plex.library.section(self.config.get("section", "TV Shows"))

    def _search_series(self, query):
        return self._section.searchShows(title=query)

    def _get_library_series(self, series):
        try:
            return self._section.get(series.name)
        except NotFound:
            results = self._search_series(series.name)
            if len(results) == 1:
                return results[0]
        return None

    def get_all_series_names(self):
        return [show.title for show in self._section.all()]

    def get_all_series_media(self, series):
        library_series = self._get_library_series(series)
        if not library_series:
            return

        for episode in library_series.episodes():
            for media in episode.media:
                yield MediaMetadata(
                    season_number=str(episode.seasonNumber),
                    episode_number=str(episode.index),
                    library_id=str(media.id),
                    video_codec=media.videoCodec,
                    audio_codec=media.audioCodec,
                    width=media.width,
                    height=media.height,
                    duration=media.duration,
                    bitrate=media.bitrate,
                    path=media.parts[0].file,
                    size=0,  # TODO: ???
                )
