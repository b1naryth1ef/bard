from flask import Blueprint, request, redirect, flash
from bard.providers import providers
from bard.models.torrent import Torrent
from bard.util.deco import model_getter, acl


torrents = Blueprint('torrents', __name__)
torrent_getter = model_getter(Torrent)


@torrents.route('/torrents/<id>/delete')
@torrent_getter
@acl('admin')
def torrents_index(torrent):
    providers.fetch.remove(torrent)
    torrent.delete_instance()

    flash('Deleted Torrent', category='success')
    return redirect(request.referrer)


@torrents.route('/torrents/<id>/process')
@torrent_getter
@acl('admin')
def torrents_process(torrent):
    from bard.tasks.torrent import process_torrent
    info = next(providers.fetch.get_torrent_info([torrent]), None)
    process_torrent(torrent, files=info.files)
    flash('Processed torrent', category='success')
    return redirect(request.referrer)
