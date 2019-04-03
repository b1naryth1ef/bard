from httplib import BAD_REQUEST
from peewee import IntegrityError
from flask import Blueprint, request, redirect, render_template, flash
from bard.providers import providers
from bard.models.series import Series
from bard.util.deco import model_getter, acl


series = Blueprint('series', __name__)
series_getter = model_getter(Series)


@series.route('/series/search')
@acl('guest')
def series_search():
    query = request.values.get('query')
    if not query:
        return 'Invalid Query', BAD_REQUEST

    search_results = providers.info.search_series(query)
    return render_template('series/search_results.html', query=query, results=search_results)


@series.route('/series/go')
@acl('guest')
def series_go():
    query = request.values.get('query')
    if not query:
        return 'Invalid Query', BAD_REQUEST

    try:
        series = Series.select().where(Series.name ** ('%' + query.lower() + '%')).get()
    except Series.DoesNotExist:
        flash('Could not find that series', category='error')
        return redirect('/')
    return redirect('/series/{}'.format(series.id))


@series.route('/series/add')
@acl('user')
def series_add():
    from bard.tasks.series import update_series

    provider_id = request.values.get('provider_id')
    series = providers.info.get_series(provider_id)
    if series:
        try:
            series.save()
        except IntegrityError:
            flash('{} is already a tracked series'.format(series.name), category='error')
        else:
            update_series(series)
            flash('Added {} to tracked series'.format(series.name), category='success')
    else:
        flash('Unknown Provider ID ({})'.format(provider_id), category='error')
    return redirect('/series')


@series.route('/series/<id>/update')
@series_getter
@acl('admin')
def series_update(series):
    from bard.tasks.series import update_series
    update_series(series)
    flash('Ok, updated {}'.format(series.name), category='success')
    return redirect(request.referrer)


@series.route('/series/<id>')
@series_getter
@acl('guest')
def series_index(series):
    return render_template('series/index.html', series=series)


@series.route('/series/<id>/sub')
@series_getter
@acl('user')
def series_sub(series):
    if not series.subscribed:
        series.subscribed = True
        series.save()
        flash('Subscribed to {}'.format(series.name), category='success')
    else:
        flash('Already subscribed to {}'.format(series.name), category='error')
    return redirect(request.referrer)


@series.route('/series/<id>/unsub')
@series_getter
@acl('user')
def series_unsub(series):
    if series.subscribed:
        series.subscribed = False
        series.save()
        flash('Unsubscribed from {}'.format(series.name), category='success')
    else:
        flash('Not subscribed to {}'.format(series.name), category='error')
    return redirect(request.referrer)


@series.route('/series/<id>/delete')
@series_getter
@acl('admin')
def series_delete(series):
    series.delete_instance()
    flash('Ok, deleted series {}'.format(series.name), category='success')
    return redirect('/')
