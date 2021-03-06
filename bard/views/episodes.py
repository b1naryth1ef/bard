try:
    from httplib import NOT_MODIFIED
except ImportError:
    from http.client import NOT_MODIFIED

from flask import Blueprint, request, redirect, render_template, flash

from bard.models import database
from bard.providers import providers
from bard.util.deco import model_getter, acl
from bard.util.redirect import magic_redirect
from bard.models.episode import Episode
from bard.models.torrent import Torrent
from bard.tasks.episode import (
    find_torrent_for_episode,
    select_optimal_torrent_for_episode,
)


episodes = Blueprint("episodes", __name__)
episode_getter = model_getter(Episode)


@episodes.route("/episodes/<id>/request")
@episode_getter
@acl("user")
def episodes_request(episode):
    if episode.state != int(Episode.State.NONE):
        return redirect(request.referrer, NOT_MODIFIED)

    episode.state = Episode.State.WANTED
    episode.save()

    if episode.aired:
        torrent = find_torrent_for_episode(episode)
        if torrent:
            episode.fetch(torrent)
            flash(
                "Started download for {}".format(episode.to_string()),
                category="success",
            )
        else:
            flash(
                "Failed to find torrent for {} (will retry later)".format(
                    episode.to_string()
                ),
                category="error",
            )
    else:
        flash(
            "Marked {} for download on airdate ({})".format(
                episode.to_string(), episode.airdate
            ),
            category="success",
        )

    return magic_redirect()


@episodes.route("/episodes/<id>/skip")
@episode_getter
@acl("user")
def episodes_skip(episode):
    if episode.state == Episode.State.NONE:
        return redirect(request.referrer, NOT_MODIFIED)

    episode.state = Episode.State.NONE
    episode.save()
    return magic_redirect()


@episodes.route("/episodes/<id>/refetch")
@episode_getter
@acl("admin")
def episodes_refetch(episode):
    if episode.state != int(Episode.State.FETCHED):
        return redirect(request.referrer, NOT_MODIFIED)

    episode.state = Episode.State.WANTED
    episode.save()

    torrent = find_torrent_for_episode(episode)
    if torrent:
        episode.fetch(torrent)
        flash(
            "Started new download for {}".format(episode.to_string()),
            category="success",
        )
    else:
        flash(
            "Failed to find new torrent for {} (will retry later)".format(
                episode.to_string()
            ),
            category="error",
        )

    return magic_redirect()


@episodes.route("/episodes/<id>")
@episode_getter
@acl("guest")
def episodes_index(episode):
    return render_template("episode/index.html", episode=episode)


@episodes.route("/episodes/<id>/torrents")
@episode_getter
@acl("user")
def episodes_torrent_list(episode):
    torrents = providers.download.search(episode)

    optimal_torrent = None
    if len(torrents):
        optimal_torrent = select_optimal_torrent_for_episode(episode, torrents)

    return render_template(
        "episode/torrents.html",
        episode=episode,
        torrents=torrents,
        optimal_torrent=optimal_torrent,
    )


@episodes.route("/episodes/<id>/fetch")
@episode_getter
@acl("admin")
def episode_fetch(episode):
    torrent_provider_id = request.values.get("provider_id")

    torrents = providers.download.search(episode)
    torrent = next((i for i in torrents if i.provider_id == torrent_provider_id), None)
    if torrent:
        episode.fetch(torrent)
        flash(
            "Ok, started a download of that torrent for this episode",
            category="success",
        )
    else:
        flash("Invalid or expired torrent", category="error")

    return magic_redirect("/episodes/{}".format(episode.id))


@episodes.route("/episodes/<id>/fetch", methods=['POST'])
@episode_getter
@acl("admin")
def episode_fetch_direct(episode):
    if 'torrent' not in request.files:
        flash("No torrent provided", category="error")
        return magic_redirect("/episodes/{}/torrents".format(episode.id))

    if not request.files['torrent'].mimetype == 'application/x-bittorrent':
        flash("Invalid torrent file", category="error")
        return magic_redirect("/episodes/{}/torrents".format(episode.id))

    with database.atomic():
        torrent = Torrent.create(
            episode=episode,
            state=Torrent.State.DOWNLOADING,
            title="User Uploaded Torrent",
            size=0,
            seeders=0,
            leechers=0,
            raw=request.files["torrent"].read(),
        )

        episode.fetch_torrent(torrent)

    flash("Ok, started a download of that torrent for this episode", category="success")
    return magic_redirect("/episodes/{}".format(episode.id))