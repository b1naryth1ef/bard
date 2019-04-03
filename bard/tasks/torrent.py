import os
import shutil
import rarfile
import logging

from bard import config
from bard.providers import providers
from bard.models.torrent import Torrent

log = logging.getLogger(__name__)


def update_torrents():
    torrents = {
        i.fetch_provider_id: i for i in Torrent.select().where(
            (Torrent.state == Torrent.State.DOWNLOADING)
        )
    }

    log.info('Updating %s torrents that are DOWNLOADING', len(torrents))

    torrent_infos = list(providers.fetch.get_torrent_info(torrents.values()))
    for torrent_info in torrent_infos:
        torrent = torrents.pop(torrent_info.id)
        torrent.state = torrent_info.state
        torrent.done_date = torrent_info.done_date
        torrent.save()

        if torrent.state in (Torrent.State.SEEDING, Torrent.State.COMPLETED):
            process_torrent(torrent, torrent_info.files)

    # TODO: check if we have anything left in torrents
    return len(torrent_infos)


def _get_result_path(torrent, ext='mkv'):
    """
    Returns the resulting path for a givent torrent file
    """
    return os.path.join(
        config['directories']['output'],
        torrent.episode.season.series.storage_name,
        '{}.{}.{}'.format(
            torrent.episode.season.series.storage_name,
            torrent.episode.season_episode_id,
            ext
        )
    )


def _store_torrent_media(torrent, source_path, keep=False):
    final_destination_path = _get_result_path(torrent)
    final_destination_dir = os.path.dirname(final_destination_path)

    # If the path doesn't exist, attempt to make it
    if not os.path.exists(final_destination_dir):
        os.mkdir(final_destination_dir)

    try:
        if keep:
            shutil.copy(source_path, final_destination_path)
        else:
            os.rename(source_path, final_destination_path)
    except:
        log.exception(
            'Failed to store torrent media (%s) %s -> %s (keep=%s): ',
            torrent.id,
            source_path,
            final_destination_path,
            keep,
        )
        raise

    os.chmod(final_destination_path, 0o777)


def process_torrent(torrent, files):
    log.debug('Processing torrent %s', torrent.id)

    try:
        # If the torrent contains a rar file attempt to unpack that
        rar_files = [i for i in files if i.endswith('.rar')]
        if len(rar_files) == 1:
            log.debug('Found rar file in torrent %s, unpacking...', torrent.id)
            unpack_torrent(torrent, rar_files[0])
            return
        elif len(rar_files) > 1:
            log.error('Found multiple rar files in torrent %s (%s)', torrent.id, rar_files)
            return

        video_files = [i for i in files if i.endswith('mkv')]
        if len(video_files) == 1:
            log.debug('Found video file in torrent %s, moving and reverse symlinking', torrent.id)
            source_path = os.path.join(config['directories']['input'], video_files[0])
            _store_torrent_media(torrent, source_path, keep=True)
            return
        elif len(video_files) > 1:
            log.error('Found multiple video files in torrent %s (%s)', torrent.id, video_files)
            return
    finally:
        torrent.processed = True
        torrent.save()


def unpack_torrent(torrent, rar_file):
    full_path = os.path.join(config['directories']['input'], rar_file)
    if not os.path.exists(full_path):
        log.error('Couldn\'t find correct path while unpacking torrent; %s', full_path)
        return

    rf = rarfile.RarFile(full_path)

    video_files = [i for i in rf.namelist() if i.endswith('.mkv')]
    if len(video_files) != 1:
        log.error('Failed to find video file to unpack from rar %s (%s)', torrent.id, rf.namelist())
        return

    temporary_dir = config['directories']['temporary']
    rf.extract(video_files[0], temporary_dir)
    _store_torrent_media(torrent, os.path.join(temporary_dir, video_files[0]))
