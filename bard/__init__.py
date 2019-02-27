from flask import Flask, request, g
from holster.flask_ext import ViewFinder
from holster.util import SimpleObject

from .constants import ACL_GROUPS
from .models import init_db
from .config import BardConfig


bard = SimpleObject()
bard.app = Flask(__name__)
bard.config = BardConfig.load()
bard.app.secret_key = bard.config['web']['secret_key']
bard.providers = SimpleObject()

for view in ViewFinder.get_views():
    bard.app.register_blueprint(view)


def before_first_request():
    from .providers import load_provider
    from .providers.info import INFO_PROVIDERS
    from .providers.download import DOWNLOAD_PROVIDERS
    from .providers.fetch import FETCH_PROVIDERS
    from .providers.notify import NOTIFY_PROVIDERS
    from .providers.library import LIBRARY_PROVIDERS

    # Load providers

    bard.providers.info = load_provider(bard, INFO_PROVIDERS, bard.config['providers']['info'])
    bard.providers.download = load_provider(bard, DOWNLOAD_PROVIDERS, bard.config['providers']['download'])
    bard.providers.fetch = load_provider(bard, FETCH_PROVIDERS, bard.config['providers']['fetch'])
    bard.providers.notify = load_provider(bard, NOTIFY_PROVIDERS, bard.config['providers']['notify'])
    bard.providers.library = load_provider(bard, LIBRARY_PROVIDERS, bard.config['providers']['library'])

    # Initialize DB
    init_db(bard)


def before_request():
    g.user = None
    g.acl = 'admin'

    user_header = bard.config['web'].get('user_header')
    if user_header:
        g.user = request.headers.get(user_header)
        g.acl = bard.config['acls'].get(g.user, 'guest')

    if g.acl not in ACL_GROUPS:
        g.acl = 'guest'


bard.app.before_first_request(before_first_request)
bard.app.before_request(before_request)
