from datetime import datetime, timedelta

from flask import Blueprint, redirect, request, flash, render_template

from bard.util.deco import acl
from bard.models.series import Series
from bard.models.season import Season
from bard.models.episode import Episode
from bard.models.torrent import Torrent


dashboard = Blueprint('dashboard', __name__)


def _dashboard_args():
    return {
            'series': Series.select().order_by(Series.subscribed.desc(), Series.name),
            'recently_aired_episodes': Episode.select().join(Season).join(Series).where(
                (Series.subscribed >> True) &
                (Episode.airdate < datetime.utcnow()) &
                (Episode.airdate > datetime.utcnow() - timedelta(days=13))
            ).order_by(Episode.airdate.desc()).limit(25),
            'upcoming_episodes': Episode.select().join(Season).join(Series).where(
                (Series.subscribed >> True) &
                (Episode.airdate > datetime.utcnow()) &
                (Episode.airdate < datetime.utcnow() + timedelta(days=7))
            ).order_by(Episode.airdate.asc()).limit(25),
            'active_torrents': Torrent.select().where(
                (Torrent.state == int(Torrent.State.DOWNLOADING)) |
                (Torrent.state == int(Torrent.State.SEEDING))
            ).order_by(Torrent.state.asc()),
            # Stalled torrents are torrents that have been downloaded but have
            #  not shown up in our library.
            'stalled_episodes': Episode.select().join(Torrent).where(
                (Torrent.state << (int(Torrent.State.SEEDING), int(Torrent.State.COMPLETED))) &
                (Episode.state == int(Episode.State.FETCHED))
            ).limit(25),
            # Dead episodes are episodes which are wanted and have aired in the
            #  past, but we've yet to fetch a torrent for them.
            'dead_episodes': Episode.select().where(
                (Episode.airdate < datetime.utcnow()) &
                (Episode.state == int(Episode.State.WANTED))
            ).limit(25),
    }


@dashboard.route('/')
@dashboard.route('/episodes')
@dashboard.route('/series')
@dashboard.route('/torrents')
@dashboard.route('/tasks')
@acl('guest')
def dashboard_index():
    parts = []
    if request.path != '/':
        parts = [request.path[1:]]

    return render_template(
        'dashboard/index.html',
        parts=parts,
        **_dashboard_args()
    )


@dashboard.route('/tasks/find-episodes')
@acl('admin')
def dashboard_tasks_find_episodes():
    from bard.tasks.episode import find_episodes
    flash('Found {} episodes'.format(find_episodes()), category='success')
    return redirect(request.referrer)


@dashboard.route('/tasks/update-torrents')
@acl('admin')
def dashboard_tasks_update_torrents():
    from bard.tasks.torrent import update_torrents
    flash('Updated {} torrents'.format(update_torrents()), category='success')
    return redirect(request.referrer)


@dashboard.route('/tasks/scan-library')
@acl('admin')
def dashboard_tasks_scan_library():
    from bard.tasks.library import scan_library
    flash('Scanned {} library media items'.format(scan_library()), category='success')
    return redirect(request.referrer)


@dashboard.route('/tasks/update-all-series')
@acl('admin')
def dashboard_tasks_update_all_series():
    from bard.tasks.series import update_all_series
    update_all_series()
    flash('Updated all series', category='success')
    return redirect(request.referrer)
