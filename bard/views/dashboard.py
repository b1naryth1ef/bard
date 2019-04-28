from datetime import datetime, timedelta

from flask import Blueprint, request, render_template

from bard.util.deco import acl
from bard.models.series import Series
from bard.models.season import Season
from bard.models.episode import Episode
from bard.models.torrent import Torrent
from bard.models.task import Task


dashboard = Blueprint('dashboard', __name__)


def _dashboard_args():
    return {
        'tasks': Task.select().order_by(Task.name),
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
