import os
import shutil
import rarfile
import logging
import mimetypes

from datetime import datetime

from bard.app import config
from bard.providers import providers
from bard.models.torrent import Torrent

log = logging.getLogger(__name__)


def _is_video_file(filename):
    mime, _ = mimetypes.guess_type(filename)
    if mime and mime.startswith("video/"):
        return True

    return False


def update_torrents():
    torrents = {
        i.fetch_provider_id: i
        for i in Torrent.select().where(
            (Torrent.state == Torrent.State.DOWNLOADING)
            | (Torrent.state == Torrent.State.SEEDING)
        )
    }
    if not torrents:
        return

    log.debug("Updating %s torrents that are DOWNLOADING or SEEDING", len(torrents))

    torrent_infos = list(providers.fetch.get_torrent_info(torrents.values()))
    for torrent_info in torrent_infos:
        torrent = torrents.pop(torrent_info.id)

        torrent.state = torrent_info.state
        torrent.save()

        if not torrent.processed and torrent.state in (Torrent.State.SEEDING, Torrent.State.COMPLETED):
            process_torrent(torrent, torrent_info.files)

    # TODO: check if we have anything left in torrents
    return len(torrent_infos)


def _get_result_path(torrent, ext=".mkv"):
    """
    Returns the resulting path for a givent torrent file
    """
    return os.path.join(
        config["directories"]["output"],
        torrent.episode.season.series.storage_name,
        "{}.{}{}".format(
            torrent.episode.season.series.storage_name,
            torrent.episode.season_episode_id,
            ext,
        ),
    )


def _store_torrent_media(torrent, source_path, keep=False):
    _, ext = os.path.splitext(source_path)
    if not ext:
        log.error("Unknown source_path extension: %s", source_path)
        return

    final_destination_path = _get_result_path(torrent, ext)
    final_destination_dir = os.path.dirname(final_destination_path)

    # If the path doesn't exist, attempt to make it
    if not os.path.exists(final_destination_dir):
        os.mkdir(final_destination_dir)

    try:
        if keep:
            shutil.copy(source_path, final_destination_path)
        else:
            os.rename(source_path, final_destination_path)
    except Exception:
        log.exception(
            "Failed to store torrent media (%s) %s -> %s (keep=%s): ",
            torrent.id,
            source_path,
            final_destination_path,
            keep,
        )
        raise

    os.chmod(final_destination_path, 0o777)


def process_torrent(torrent, files):
    log.info("Processing torrent %s", torrent.id)

    # Mark the torrent as processed now so nobody else tries to process
    torrent.processed = True
    torrent.save()

    # If the torrent contains a rar file attempt to unpack that
    rar_files = [i for i in files if i.endswith(".rar")]
    if len(rar_files):
        log.debug("Found rar file in torrent %s, unpacking...", torrent.id)
        unpack_torrent(torrent, rar_files[0])
        return

    video_files = [i for i in files if _is_video_file(i)]
    if len(video_files) == 1:
        log.debug(
            "Found video file in torrent %s, moving and reverse symlinking",
            torrent.id,
        )
        source_path = os.path.join(config["directories"]["input"], video_files[0])
        _store_torrent_media(torrent, source_path, keep=True)
        return
    elif len(video_files) > 1:
        log.error(
            "Found multiple video files in torrent %s (%s)", torrent.id, video_files
        )
        return


def unpack_torrent(torrent, rar_file):
    full_path = os.path.join(config["directories"]["input"], rar_file)
    if not os.path.exists(full_path):
        log.error("Couldn't find correct path while unpacking torrent; %s", full_path)
        return

    rf = rarfile.RarFile(full_path)

    video_files = [i for i in rf.namelist() if _is_video_file(i)]
    if len(video_files) != 1:
        log.error(
            "Failed to find video file to unpack from rar %s (%s)",
            torrent.id,
            rf.namelist(),
        )
        return

    temporary_dir = config["directories"]["temporary"]
    rf.extract(video_files[0], temporary_dir)
    _store_torrent_media(torrent, os.path.join(temporary_dir, video_files[0]))


def prune_torrents():
    if not config["seed_days"]:
        return

    seeding = {
        i.fetch_provider_id: i
        for i in Torrent.select().where((Torrent.state == Torrent.State.SEEDING))
    }

    torrent_infos = providers.fetch.get_torrent_info(seeding.values())
    for info in torrent_infos:
        approx_seeding_duration = (
            datetime.utcnow() - info.done_date.replace(tzinfo=None)
        ).days
        if approx_seeding_duration > config["seed_days"]:
            log.info(
                "Pruning torrent %s which has seeded for %s days (%ss)",
                info.id,
                approx_seeding_duration,
                info.seconds_seeding,
            )
            seeding[info.id].state = Torrent.State.COMPLETED
            seeding[info.id].save()
            providers.fetch.remove(seeding[info.id])
