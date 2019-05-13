import logging

from bard.providers import providers
from bard.models.episode import Episode

log = logging.getLogger(__name__)


def update_season(season):
    log.info(
        "Performing an update on season %s, %s (%s)",
        season.number,
        season.series.name,
        season.series.id,
    )

    for episode_info in providers.info.get_episodes(season.series, season.number):
        try:
            episode = Episode.get(season=season, number=episode_info.number)
            episode.update_from_metadata(episode_info)
            episode.save()
        except Episode.DoesNotExist:
            episode = Episode.from_metadata(
                season,
                episode_info,
                state=Episode.State.WANTED if season.subscribed else Episode.State.NONE,
            )
            log.info(
                "Added episode %s in state %s due to season %s being subscribed (%s)",
                episode.id,
                episode.state,
                season.id,
                season.subscribed,
            )
