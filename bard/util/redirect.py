from flask import request, redirect


def magic_redirect(to=None):
    if request.values.get("r"):
        # NB: technically an open redirect
        return redirect(request.values["r"])

    if request.referrer.endswith(request.path):
        return redirect("/")

    if to and to != request.path:
        return redirect(to)

    return redirect(request.referrer)
