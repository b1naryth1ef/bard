import os
import logging

from datetime import datetime
from holster.tasks import task

from bard import bard
from bard.constants import QUALITIES
from bard.models.episode import Episode
from bard.models.torrent import Torrent

log = logging.getLogger(__name__)


def find_torrent_for_episode(episode):
    log.debug('Searching for episode `%s`', episode)
    results = bard.providers.download.search(episode)

    if not len(results):
        log.debug('Failed to find any torrents for episode `%s`', episode)
        return None

    # Filter out torrents we've already fetched
    existing_torrents = Torrent.select(Torrent.provider_id).where(
        (Torrent.episode == episode)
    )
    existing_torrent_ids = [i.provider_id for i in existing_torrents]
    results = [i for i in results if i.id not in existing_torrent_ids]

    if not len(results):
        log.debug('Excluded all torrents based on previous fetches for episode `%s`', episode)
        return None

    # Store the results by seeders
    results = sorted(results, key=lambda i: i.seeders, reverse=True)

    desired_quality = episode.quality or bard.config.get('default_quality')

    # If no quality preference is selected, return the highest seeder count
    if desired_quality is None:
        return results[0]

    # Sort episodes by quality, this is so we don't include 720p/1080p with
    #  the default "no" quality (aka empty string)
    qualities = {}
    for quality in QUALITIES:
        qualities[quality] = filter(lambda k: quality in k.title.lower(), results)

    if qualities[desired_quality]:
        return qualities[desired_quality][0]
    return results[0]


@task()
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


@task()
def post_process_episode(episode_id):
    log.info('Post-processing E%s', episode_id)
    episode = Episode.get(id=episode_id)

    # Grab the torrent
    torrent = list(episode.torrents)[-1]

    for path in torrent.get_files():
        path = os.path.join(bard.config.directories['input'], path)
        print path
        print os.path.exists(path)
