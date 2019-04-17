import logging
from bard.providers import providers
from bard.models.episode import Episode

log = logging.getLogger(__name__)


def update_season(season):
    log.info('Performing an update on season %s, %s (%s)', season.number, season.series.name, season.series.id)

    for episode in providers.info.get_episodes(season.series.provider_id, season.number):
        try:
            existing_episode = Episode.select().where(
                (Episode.season == season) &
                (Episode.number == episode.number)
            ).get()
            existing_episode.merge(episode)
            episode = existing_episode
        except Episode.DoesNotExist:
            episode.season = season

            # If subscribed, mark this episode as wanted
            if season.subscribed:
                episode.state = episode.State.WANTED

        episode.save()
