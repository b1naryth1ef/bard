try:
    from httplib import BAD_REQUEST
except ImportError:
    from http.client import BAD_REQUEST

from datetime import datetime

from peewee import IntegrityError
from flask import Blueprint, request, redirect, render_template, flash

from bard.models import database
from bard.providers import providers
from bard.models.series import Series
from bard.models.episode import Episode
from bard.util.deco import model_getter, acl


series = Blueprint("series", __name__)
series_getter = model_getter(Series)


@series.route("/series/search")
@acl("guest")
def series_search():
    query = request.values.get("query")
    if not query:
        return "Invalid Query", BAD_REQUEST

    search_results = providers.info.search_series(query)
    return render_template(
        "series/search_results.html", query=query, results=search_results
    )


@series.route("/series/go")
@acl("guest")
def series_go():
    query = request.values.get("query")
    if not query:
        return "Invalid Query", BAD_REQUEST

    try:
        series = Series.select().where(Series.name ** ("%" + query.lower() + "%")).get()
    except Series.DoesNotExist:
        flash("Could not find that series", category="error")
        return redirect("/")
    return redirect("/series/{}".format(series.id))


@series.route("/series/add")
@acl("user")
def series_add():
    from bard.tasks.series import update_series

    provider_id = request.values.get("provider_id")
    series_info = providers.info.get_series_by_provider_id(provider_id)

    # Attempt to link in provider_ids from non-search providers
    providers.info.link_series_providers(series_info)

    if series_info:
        series = None

        try:
            series = Series.from_metadata(series_info)
        except IntegrityError:
            flash(
                "{} is already a tracked series".format(series_info.name),
                category="error",
            )
        else:
            update_series(series)
            flash(
                "Added {} to tracked series".format(series_info.name),
                category="success",
            )
            return redirect("/series/{}".format(series.id))
    else:
        flash("Unknown Provider ID ({})".format(provider_id), category="error")

    return redirect("/series")


@series.route("/series/<id>/update")
@series_getter
@acl("admin")
def series_update(series):
    from bard.tasks.series import update_series

    update_series(series)
    flash("Ok, updated {}".format(series.name), category="success")
    return redirect(request.referrer)


@series.route("/series/<id>")
@series_getter
@acl("guest")
def series_index(series):
    return render_template("series/index.html", series=series)


@series.route("/series/<id>/sub")
@series_getter
@acl("user")
def series_sub(series):
    if series.subscribed:
        flash("Already subscribed to {}".format(series.name), category="error")
    else:
        # When subscribing to a series we need to look for all unaired episodes
        #  and mark them as wanted. We don't mark previously aired episodes as
        #  wanted because its less clear if the user wants that (whereas them saying
        #  they want all future episodes of the show, and us marking all future
        #  episodes as wanted is understandable)
        with database.atomic():
            episodes_marked = (
                Episode.update(state=Episode.State.WANTED)
                .where(
                    (Episode.state == Episode.State.NONE)
                    & (
                        (~(Episode.airdate >> None))
                        & (Episode.airdate > datetime.utcnow())
                    )
                )
                .execute()
            )

            series.subscribed = True
            series.save()

        flash(
            "Subscribed to {} and marked {} future episodes as wanted".format(
                series.name, episodes_marked
            ),
            category="success",
        )

    return redirect(request.referrer)


@series.route("/series/<id>/unsub")
@series_getter
@acl("user")
def series_unsub(series):
    if series.subscribed:
        series.subscribed = False
        series.save()
        flash("Unsubscribed from {}".format(series.name), category="success")
    else:
        flash("Not subscribed to {}".format(series.name), category="error")
    return redirect(request.referrer)


@series.route("/series/<id>/delete")
@series_getter
@acl("admin")
def series_delete(series):
    series.delete_instance()
    flash("Ok, deleted series {}".format(series.name), category="success")
    return redirect("/")
