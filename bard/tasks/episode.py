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

    return select_optimal_torrent_for_episode(episode, results)


def select_optimal_torrent_for_episode(episode, torrents):
    # Filter out torrents we've already fetched
    existing_torrent_ids = (
        Torrent.select(Torrent.download_provider_id)
        .where(
            (Torrent.episode == episode)
            & (Torrent.download_provider == torrents[0].provider)
        )
        .objects(_download_provider_id)
    )
    torrents = [i for i in torrents if i.provider_id not in existing_torrent_ids]

    if not len(torrents):
        return None

    # Store the torrents by seeders
    torrents = sorted(torrents, key=lambda i: i.seeders, reverse=True)

    # If we have any preferred keywords use them to sort our torrents now
    preferred_keywords = config["quality"].get("preferred_keywords")
    if preferred_keywords is not None:
        torrents = sorted(
            torrents,
            key=lambda i: 0
            if any(
                (keyword.lower() in i.title.lower()) for keyword in preferred_keywords
            )
            else 1,
        )

    # If we have no quality preferences set in the config, return the highest
    #  seeder count result.
    desired_quality = config["quality"].get("desired")
    if desired_quality is None:
        return torrents[0]

    # If we're still in the time window defined by max_wait_minutes and calculated
    #  based on the episode airdate, that means we won't accept torrents detected
    #  as a lower quality.
    max_wait_minutes = config["quality"].get("max_wait_minutes")
    if max_wait_minutes:
        cutoff = episode.airdate + timedelta(minutes=max_wait_minutes)
        if datetime.utcnow() < cutoff:
            # Filter to only torrents matching our desired quality
            torrents = [i for i in torrents if desired_quality in i.title.lower()]

            # If we have any torrents at our desired quality, return highest seed
            #  count
            if torrents:
                return torrents[0]

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
        for result in torrents:
            if quality in result.title.lower():
                return result

    # Just return the highest seeder count result
    return torrents[0]


def find_episodes():
    episodes = Episode.select().where(
        (Episode.state == Episode.State.WANTED)
        & ((~(Episode.airdate >> None)) & (Episode.airdate < datetime.utcnow()))
    )

    count = 0
    for episode in episodes:
        torrent = find_torrent_for_episode(episode)
        if not torrent:
            log.info("Failed to find torrent for episode %s", episode.to_string())
            continue

        count += 1
        episode.fetch(torrent)

    return count
