#!/usr/bin/env python
from __future__ import print_function

from gevent import monkey
monkey.patch_all()  # noqa: E402

import gevent
import logging
import click

from werkzeug.serving import run_with_reloader
from gevent import pywsgi
from bard.app import app, config, before_first_request
from bard.cron import scheduler as cron_scheduler, init_cron

log = logging.getLogger(__name__)


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
        init_cron()
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
    init_cron()
    cron_scheduler.run()


@cli.command('update-media-sizes')
def update_media_sizes():
    """
    Updates the on-disk size of all media items.
    """
    from bard.models.media import Media
    from bard.tasks.library import get_path_size_on_disk

    for media in Media.select():
        media.size = get_path_size_on_disk(media.path)
        if media.size:
            media.save()


@cli.command('link-provider')
@click.argument('provider-name')
def link_provider(provider_name):
    from bard import providers
    from bard.models.series import Series

    if provider_name not in providers.info._providers:
        print('Error: `{}` is not a configured info provider'.format(provider_name))
        return

    provider = providers.info._providers[provider_name]

    unlinked_series = Series.select().where(
        (Series.provider_ids[provider_name] >> None)
    )
    for series in unlinked_series:
        info = provider.find_by_external(series.provider_ids)
        if info:
            log.info('Linked series %r via find_by_external', series)
            series.provider_ids[provider_name] = info.provider_ids[provider_name]
            series.save()
            continue

        results = provider.search_series(series.name)
        if len(results) == 1:
            log.info('Linked series %r via search_series', series)
            series.provider_ids[provider_name] = results[0].provider_ids[provider_name]
            series.save()
            continue

        log.info('Series %r was unable to be linked (%s results)', series, len(results))


@cli.command('prune-missing-media')
def prune_missing_media():
    from bard.tasks.media import prune_missing_media
    prune_missing_media()


if __name__ == '__main__':
    cli(obj={})
