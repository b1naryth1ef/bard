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
    return os.path.join(
        bard.config['directories']['output'],
        torrent.episode.season.series.storage_name,
        '{}.{}.mkv'.format(
            torrent.episode.season.series.storage_name,
            torrent.episode.season_episode_id,
        )
    )


@task()
def process_torrent(torrent):
    log.debug('Processing torrent %s', torrent.id)

    # Get the list of files
    files = bard.providers.fetch.get_files(torrent)
    result_file = None

    # This really just means we tried to extract some media from the torrent
    torrent.processed = True
    torrent.save()

    # First, check if this is compressed
    rar_files = [i for i in files if i.endswith('.rar')]
    if len(rar_files) == 1:
        log.debug('Found rar file in torrent %s, unpacking...', torrent.id)
        result_file = unpack_torrent(torrent, rar_files[0])
        if not result_file:
            return
    elif len(rar_files) > 1:
        log.error('Found multiple rar files in torrent %s (%s)', torrent.id, rar_files)
        return
    else:
        video_files = [i for i in files if i.endswith('mkv')]

        if len(video_files) == 1:
            log.debug('Found video file in torrent %s, moving and reverse symlinking', torrent.id)
            source_path = os.path.join(bard.config['directories']['input'], video_files[0])
            dest_path = _get_result_path(torrent)
            shutil.copy(source_path, dest_path)
            os.chmod(dest_path, 0777)
            return

        log.error('Found no rar file in torrent %s, skipping', torrent.id)
        return


@task()
def unpack_torrent(torrent, rar_file):
    full_path = os.path.join(bard.config['directories']['input'], rar_file)
    if not os.path.exists(full_path):
        log.error('Couldn\'t find correct path while unpacking torrent; %s', full_path)
        return

    rf = rarfile.RarFile(full_path)
    names = [i for i in rf.namelist() if i.endswith('.mkv')]
    if len(names) != 1:
        log.error('Failed to find mkv file in namelist; %s', rf.namelist())
        return

    final_path = _get_result_path(torrent)
    out_dir = os.path.dirname(final_path)

    if not os.path.exists(out_dir):
        os.mkdir(out_dir)

    log.info('Attempting to unpack %s from %s to %s', names[0], full_path, out_dir)
    rf.extract(names[0], out_dir)

    os.rename(os.path.join(out_dir, names[0]), final_path)
    os.chmod(final_path, 0777)
    return final_path
