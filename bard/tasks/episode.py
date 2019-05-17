import logging
from datetime import datetime, timedelta

from bard.app import config
from bard.providers import providers
from bard.constants import QUALITIES
from bard.models.episode import Episode
from bard.models.torrent import Torrent

log = logging.getLogger(__name__)


def _download_provider_id(download_provider_id):
    return download_provider_id


def find_torrent_for_episode(episode):
    log.debug("Searching for episode `%s`", episode)

    results = providers.download.search(episode)

    if not len(results):
        log.debug("Failed to find any torrents for episode `%s`", episode)
        return None

    # Filter out torrents we've already fetched
    existing_torrent_ids = (
        Torrent.select(Torrent.download_provider_id)
        .where(
            (Torrent.episode == episode)
            & (Torrent.download_provider == results[0].provider)
        )
        .objects(_download_provider_id)
    )
    results = [i for i in results if i.provider_id not in existing_torrent_ids]

    if not len(results):
        log.debug(
            "Excluded all torrents based on previous fetches for episode `%s`", episode
        )
        return None

    # Store the results by seeders
    results = sorted(results, key=lambda i: i.seeders, reverse=True)

    # If we have no quality preferences set in the config, return the highest
    #  seeder count result.
    desired_quality = config["quality"].get("desired")
    if desired_quality is None:
        return results[0]

    # If we're still in the time window defined by max_wait_minutes and calculated
    #  based on the episode airdate, that means we won't accept torrents detected
    #  as a lower quality.
    max_wait_minutes = config["quality"].get("max_wait_minutes")
    if max_wait_minutes:
        cutoff = episode.airdate + timedelta(minutes=max_wait_minutes)
        if datetime.utcnow() < cutoff:
            # Filter to only results matching our desired quality
            results = [i for i in results if desired_quality in i.title.lower()]

            # If we have any results at our desired quality, return highest seed
            #  count
            if results:
                return results[0]

            # Otherwise return nothing and we'll try again later
            return None

    # Grab qualities and order by highest first
    qualities_to_check = list(reversed(QUALITIES))

    # If we have a desired quality we want to search by that first, and then go
    #  based on highest to lowest quality.
    if desired_quality:
        qualities_to_check.remove(desired_quality)
        qualities_to_check = [desired_quality] + qualities_to_check

    for quality in qualities_to_check:
        for result in results:
            if quality in result.title.lower():
                return result

    # Just return the highest seeder count result
    return results[0]


def find_episodes():
    episodes = Episode.select().where(
        (Episode.state == Episode.State.WANTED)
        & ((~(Episode.airdate >> None)) & (Episode.airdate < datetime.utcnow()))
    )

    count = 0
    for episode in episodes:
        if not episode.airdate:
            continue

        torrent = find_torrent_for_episode(episode)
        if not torrent:
            log.info("Failed to find torrent for episode %s", episode.to_string())
            continue

        count += 1
        episode.fetch(torrent)

    return count
