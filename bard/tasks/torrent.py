import os
import shutil
import rarfile
import logging
from holster.tasks import task

from bard import bard
from bard.models.torrent import Torrent

log = logging.getLogger(__name__)


@task()
def update_torrents():
    torrents = list(Torrent.select().where(
        (Torrent.state == Torrent.State.DOWNLOADING)
    ))

    log.info('Updating %s torrents that are DOWNLOADING', len(torrents))

    for torrent in torrents:
        status = bard.providers.fetch.get_status(torrent)
        if not status:
            continue
        torrent.state = status['state']
        torrent.save()

        if torrent.state in (Torrent.State.SEEDING, Torrent.State.COMPLETED):
            process_torrent(torrent)

    return len(torrents)


def _get_result_path(torrent, ext='mkv'):
    """
    Returns the resulting path for a givent torrent file
    """
    return os.path.join(
        bard.config['directories']['output'],
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

    if keep:
        shutil.copy(source_path, final_destination_path)
    else:
        os.rename(source_path, final_destination_path)

    os.chmod(final_destination_path, 0777)


@task()
def process_torrent(torrent):
    log.debug('Processing torrent %s', torrent.id)

    # Get the list of files
    files = bard.providers.fetch.get_files(torrent)

    # This really just means we tried to extract some media from the torrent
    torrent.processed = True
    torrent.save()

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
        source_path = os.path.join(bard.config['directories']['input'], video_files[0])
        _store_torrent_media(torrent, source_path, keep=True)
        return
    elif len(video_files) > 1:
        log.error('Found multiple video files in torrent %s (%s)', torrent.id, video_files)
        return


@task()
def unpack_torrent(torrent, rar_file):
    full_path = os.path.join(bard.config['directories']['input'], rar_file)
    if not os.path.exists(full_path):
        log.error('Couldn\'t find correct path while unpacking torrent; %s', full_path)
        return

    rf = rarfile.RarFile(full_path)

    video_files = [i for i in rf.namelist() if i.endswith('.mkv')]
    if len(video_files) != 1:
        log.error('Failed to find video file to unpack from rar %s (%s)', torrent.id, rf.namelist())
        return

    rf.extract(video_files[0], os.path.dirname(full_path))
    _store_torrent_media(torrent, os.path.join(os.path.dirname(full_path), video_files[0]))
