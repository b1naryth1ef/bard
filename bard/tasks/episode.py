import logging
from datetime import datetime

from bard.app import config
from bard.providers import providers
from bard.constants import QUALITIES
from bard.models.episode import Episode
from bard.models.torrent import Torrent

log = logging.getLogger(__name__)


def _download_provider_id(download_provider_id):
    return download_provider_id


def find_torrent_for_episode(episode):
    log.debug('Searching for episode `%s`', episode)

    results = providers.download.search(episode)

    if not len(results):
        log.debug('Failed to find any torrents for episode `%s`', episode)
        return None

    # Filter out torrents we've already fetched
    existing_torrent_ids = Torrent.select(Torrent.download_provider_id).where(
        (Torrent.episode == episode) &
        (Torrent.download_provider == results[0].provider)
    ).objects(_download_provider_id)
    results = [i for i in results if i.provider_id not in existing_torrent_ids]

    if not len(results):
        log.debug('Excluded all torrents based on previous fetches for episode `%s`', episode)
        return None

    # Store the results by seeders
    results = sorted(results, key=lambda i: i.seeders, reverse=True)

    desired_quality = episode.quality or config.get('default_quality')

    # If no quality preference is selected, return the highest seeder count
    if desired_quality is None:
        return results[0]

    # Sort episodes by quality, this is so we don't include 720p/1080p with
    #  the default "no" quality (aka empty string)
    qualities = {}
    for quality in QUALITIES:
        qualities[quality] = [i for i in results if quality in i.title.lower()]

    if qualities[desired_quality]:
        return qualities[desired_quality][0]
    return results[0]


def find_episodes():
    episodes = Episode.select().where(
        (Episode.state == Episode.State.WANTED) &
        (
            (~(Episode.airdate >> None)) &
            (Episode.airdate < datetime.utcnow())
        )
    )

    count = 0
    for episode in episodes:
        if not episode.airdate:
            continue

        torrent = find_torrent_for_episode(episode)
        if not torrent:
            log.info('Failed to find torrent for episode %s', episode.to_string())
            continue

        count += 1
        episode.fetch(torrent)

    return count
