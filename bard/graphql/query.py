from flask import request, jsonify, render_template
from py_gql import schema, execution, process_graphql_query

from bard.models.series import Series
from bard.models.season import Season
from bard.models.episode import Episode
from bard.graphql.types import GQLSeries, GQLSeason, GQLEpisode, create_id_resolver, create_generic_resolver


query_type = schema.ObjectType(
    'Query',
    fields=[
        create_id_resolver(Series, GQLSeries, 'seriesById'),
        create_id_resolver(Season, GQLSeason, 'seasonById'),
        create_id_resolver(Episode, GQLEpisode, 'episodeById'),
        create_generic_resolver(Series, GQLSeries, 'series'),
        create_generic_resolver(Season, GQLSeason, 'seasons'),
        create_generic_resolver(Episode, GQLEpisode, 'episodes'),
    ],
)


gql_schema = schema.Schema(
    query_type=query_type,
    types=[GQLSeries, GQLSeason, GQLEpisode],
)


def gql_route():
    result = execution.Executor.unwrap_value(
        process_graphql_query(
            gql_schema,
            request.json['query'],
        )
    )

    return jsonify(result.response())


def giql_route():
    return render_template('graphql/graphiql.html')
