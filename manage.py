#!/usr/bin/env python
from __future__ import print_function

from gevent import monkey
monkey.patch_all()  # noqa: E402

import gevent
import logging
import click

from werkzeug.serving import run_with_reloader
from gevent import pywsgi
from bard import app, config, before_first_request
from bard.cron import scheduler as cron_scheduler


@click.group()
def cli():
    before_first_request()
    logging.basicConfig(level=logging.INFO)
    logging.getLogger('bard').setLevel(logging.DEBUG)
    logging.getLogger('urllib3').setLevel(logging.INFO)
    logging.getLogger('peewee').setLevel(logging.INFO)
    logging.getLogger('requests').setLevel(logging.INFO)
    logging.getLogger('pytvdbapi').setLevel(logging.INFO)


@cli.command()
@click.option('--reloader/--no-reloader', '-r', default=False)
@click.option('--scheduler/--no-scheduler', '-s', default=False)
def serve(reloader, scheduler):
    def run():
        print('Running webserver on {}:{}'.format(
            config['web']['host'],
            config['web']['port'],
        ))
        pywsgi.WSGIServer((config['web']['host'], config['web']['port']), app).serve_forever()

    if scheduler:
        # TODO: support reloading scheduler too
        assert not reloader
        gevent.spawn(cron_scheduler.run)

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
        print('Starting iPython Shell')
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
        print('Starting Poverty Shell (install IPython to use improved shell)')

    with app.app_context():
        console.interact()


@cli.command()
def resetdb():
    from bard.models import REGISTERED_MODELS, init_db

    init_db(config)

    for model in REGISTERED_MODELS:
        model.drop_table(True, False)
        model.create_table(True)


@cli.command('scheduler')
def run_scheduler():
    print('Running scheduler')
    cron_scheduler.run()


if __name__ == '__main__':
    cli(obj={})
