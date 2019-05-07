import os
from flask import Flask, request, g

from .constants import ACL_GROUPS
from .models import init_db
from .providers import providers
from .util.config import Configuration


app = Flask(__name__)
config = Configuration(
    locations=(
        os.getcwd(),
        '/etc/bard',
        '~/.config/bard',
    ),
    validations={
        'web': dict,
        'web.secret_key': str,
        'providers': dict,
        'directories': dict,
        'directories.input': str,
        'directories.output': str,
        'directories.temporary': str,
        'acls': dict,
        'database': str,
        'seed_days': int,
        'quality': dict,
        'quality.desired': str,
    },
)

app.secret_key = config['web']['secret_key']


def register_blueprints():
    from .views.dashboard import dashboard
    from .views.episodes import episodes
    from .views.media import media
    from .views.series import series
    from .views.torrents import torrents

    app.register_blueprint(dashboard)
    app.register_blueprint(episodes)
    app.register_blueprint(media)
    app.register_blueprint(series)
    app.register_blueprint(torrents)


def before_first_request():
    providers.load_from_config(config)

    # Initialize DB
    init_db(config)

    # Register all our blueprints
    register_blueprints()


def before_request():
    g.user = None
    g.acl = 'admin'

    user_header = config.get('web.user_header')
    if user_header:
        g.user = request.headers.get(user_header)
        g.acl = config['acls'].get(g.user, 'guest')

    if g.acl not in ACL_GROUPS:
        g.acl = 'guest'


app.before_first_request(before_first_request)
app.before_request(before_request)
