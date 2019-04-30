from py_gql import schema
from peewee import AutoField, CharField, IntegerField, DateTimeField, BooleanField

from bard.models.series import Series
from bard.models.season import Season
from bard.models.episode import Episode


def create_enum(enum_cls):
    values = []

    for attrib in dir(enum_cls):
        if attrib.startswith('_') or attrib == 'ALL':
            continue

        values.append((attrib, getattr(enum_cls, attrib)))

    return schema.EnumType(
        enum_cls.__name__,
        values=values,
    )


def create_id_resolver(model, gqlmodel, name):
    def resolver(*args, **kwargs):
        try:
            return model.select().where(model.id == kwargs['id']).dicts().get()
        except model.DoesNotExist:
            return None

    return schema.Field(name, gqlmodel, args=[
        schema.Argument('id', schema.ID)
    ], resolver=resolver)


def create_generic_resolver(model, gqlmodel, name):
    def resolver(*args, **kwargs):
        return list(model.select().dicts().paginate(
            kwargs['page'],
            50,
        ))

    return schema.Field(name, schema.ListType(gqlmodel), args=[
        schema.Argument('page', schema.Int),
    ], resolver=resolver)


def create_gql_from_model(model, exclude=None, fields=None):
    fields = fields.copy() if fields else []

    for name, field in model._meta.fields.items():
        if exclude and name in exclude:
            continue

        if isinstance(field, AutoField) and name == 'id':
            fields.append(schema.Field(name, schema.ID))
        elif isinstance(field, CharField):
            fields.append(schema.Field(name, schema.String))
        elif isinstance(field, IntegerField):
            fields.append(schema.Field(name, schema.Int))
        elif isinstance(field, BooleanField):
            fields.append(schema.Field(name, schema.Boolean))
        elif isinstance(field, DateTimeField):
            # TODO
            fields.append(schema.Field(name, schema.String))
        else:
            raise Exception('unsupported peewee field: {}'.format(field))

    return schema.ObjectType(
        model.__name__.lower(),
        fields=fields,
    )


def resolve_series_seasons(root, *args, **kwargs):
    return list(Season.select().where(
        Season.series == root['id']
    ).dicts())


def resolve_series_episodes(root, *args, **kwargs):
    return list(Episode.select(Episode).join(Season).where(
        Season.series == root['id']
    ).dicts())


def resolve_season_series(root, *args, **kwargs):
    return Series.select().where(
        Series.id == root['series']
    ).dicts().get()


def resolve_episode_series(root, *args, **kwargs):
    return Series.select(Series).join(Season).where(
        Season.id == root['season']
    ).dicts().get()


def resolve_episode_season(root, *args, **kwargs):
    return Season.select().where(
        Season.id == root['season']
    ).dicts().get()


GQLSeason = create_gql_from_model(Season, exclude=('series', ))
GQLEpisode = create_gql_from_model(Episode, exclude=('season', 'state'), fields=[
    schema.Field('state', create_enum(Episode.State)),
])

GQLSeries = create_gql_from_model(Series, fields=[
    schema.Field('seasons', schema.ListType(GQLSeason), resolver=resolve_series_seasons),
    schema.Field('episodes', schema.ListType(GQLEpisode), resolver=resolve_series_episodes),
    schema.Field('status', create_enum(Series.AirStatus)),
], exclude=('provider_ids', 'status'))

GQLSeason.fields.append(schema.Field('series', GQLSeries, resolver=resolve_season_series))
GQLEpisode.fields.append(schema.Field('series', GQLSeries, resolver=resolve_episode_series))
GQLEpisode.fields.append(schema.Field('season', GQLSeason, resolver=resolve_episode_season))
