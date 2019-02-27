from flask import g, redirect, request, flash
from functools import wraps

from bard.constants import ACL_GROUPS


def acl(group):
    def deco(f):
        @wraps(f)
        def _f(*args, **kwargs):
            if ACL_GROUPS.index(group) > ACL_GROUPS.index(g.acl):
                return 'Incorrect ACL', 403

            return f(*args, **kwargs)
        return _f
    return deco


def model_getter(model):
    def deco(func):
        @wraps(func)
        def _f(id, *args, **kwargs):
            try:
                result = model.select().where(model.id == id).get()
            except model.DoesNotExist:
                flash('Unknown {} {}'.format(model.__name__, id), category='error')
                return redirect('/')

            return func(result, *args, **kwargs)
        return _f
    return deco
