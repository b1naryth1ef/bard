#!/usr/bin/env python
from gevent import monkey
monkey.patch_all()  # noqa: E402

from werkzeug.serving import run_with_reloader
from gevent import pywsgi
from bard import bard, before_first_request

import logging
import click


@click.group()
def cli():
    before_first_request()
    logging.getLogger().setLevel(logging.DEBUG)
    logging.getLogger('peewee').setLevel(logging.INFO)
    logging.getLogger('requests').setLevel(logging.INFO)
    logging.getLogger('pytvdbapi').setLevel(logging.INFO)


@cli.command()
@click.option('--reloader/--no-reloader', '-r', default=False)
def serve(reloader):
    def run():
        print 'Running webserver on {}:{}'.format(
            bard.config['web']['host'],
            bard.config['web']['port'],
        )
        pywsgi.WSGIServer((bard.config['web']['host'], bard.config['web']['port']), bard.app).serve_forever()

    if reloader:
        run_with_reloader(run)
    else:
        run()


@cli.command()
def shell():
    namespace = {}

    try:
        from IPython.terminal.interactiveshell import TerminalInteractiveShell
        console = TerminalInteractiveShell(user_ns=namespace)
        print 'Starting iPython Shell'
    except ImportError:
        import code
        import rlcompleter
        c = rlcompleter.Completer(namespace)

        # Setup readline for autocomplete.
        try:
            # noinspection PyUnresolvedReferences
            import readline
            readline.set_completer(c.complete)
            readline.parse_and_bind('tab: complete')
            readline.parse_and_bind('set show-all-if-ambiguous on')
            readline.parse_and_bind('"\C-r": reverse-search-history')
            readline.parse_and_bind('"\C-s": forward-search-history')

        except ImportError:
            pass

        console = code.InteractiveConsole(namespace)
        print 'Starting Poverty Shell (install IPython to use improved shell)'

    with bard.app.app_context():
        console.interact()


@cli.command()
def resetdb():
    from bard.models import REGISTERED_MODELS, init_db
    import bard.models.episode
    import bard.models.season
    import bard.models.series
    import bard.models.torrent
    import bard.models.user

    from bard import bard
    init_db(bard)

    print REGISTERED_MODELS
    for model in REGISTERED_MODELS:
        model.drop_table(True, False)
        model.create_table(True)


@cli.command('run-task')
@click.argument('task-name')
@click.argument('args', nargs=-1)
def run_task(task_name, args):
    import bard.tasks  # noqa: F401
    from holster.tasks import _TASKS
    _TASKS.get(task_name)(*args)


if __name__ == '__main__':
    cli(obj={})
