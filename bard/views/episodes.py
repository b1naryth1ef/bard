from flask import Blueprint, request, redirect, render_template, flash
from bard.providers import providers
from bard.util.deco import model_getter, acl
from bard.util.redirect import magic_redirect
from bard.models.episode import Episode

try:
    from httplib import NOT_MODIFIED
except ImportError:
    from http.client import NOT_MODIFIED


episodes = Blueprint('episodes', __name__)
episode_getter = model_getter(Episode)


@episodes.route('/episodes/<id>/request')
@episode_getter
@acl('user')
def episodes_request(episode):
    if episode.state != int(Episode.State.NONE):
        return redirect(request.referrer, NOT_MODIFIED)

    episode.state = Episode.State.WANTED
    episode.save()
    return magic_redirect()


@episodes.route('/episodes/<id>/skip')
@episode_getter
@acl('user')
def episodes_skip(episode):
    if episode.state == Episode.State.NONE:
        return redirect(request.referrer, NOT_MODIFIED)

    episode.state = Episode.State.NONE
    episode.save()
    return magic_redirect()


@episodes.route('/episodes/<id>/refetch')
@episode_getter
@acl('admin')
def episodes_refetch(episode):
    if episode.state != int(Episode.State.FETCHED):
        return redirect(request.referrer, NOT_MODIFIED)

    episode.state = Episode.State.WANTED
    episode.save()
    return magic_redirect()


@episodes.route('/episodes/<id>')
@episode_getter
@acl('guest')
def episodes_index(episode):
    return render_template('episode/index.html', episode=episode)


@episodes.route('/episodes/<id>/torrents')
@episode_getter
@acl('user')
def episodes_torrent_list(episode):
    torrents = providers.download.search(episode)
    return render_template('episode/torrents.html', episode=episode, torrents=torrents)


@episodes.route('/episodes/<id>/fetch')
@episode_getter
@acl('admin')
def episode_fetch(episode):
    torrent_id = request.values.get('id')
    metadata = providers.download.get_torrent(torrent_id)
    if metadata:
        episode.fetch(metadata)
        flash('Ok, started a download of that torrent for this episode', category='success')
    else:
        flash('Invalid or expired torrent', category='error')
    return magic_redirect('/episodes/{}'.format(episode.id))
