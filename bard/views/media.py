from peewee import fn
from flask import Blueprint, request, render_template

from bard.util.deco import acl
from bard.models.media import Media


media = Blueprint('media', __name__)


@media.route('/media')
@acl('guest')
def media_index():
    page = int(request.values.get('page', 1))

    media = Media.select()

    if 'video_codec' in request.values:
        media = media.where(Media.video_codec == request.values['video_codec'])

    if 'audio_codec' in request.values:
        media = media.where(Media.audio_codec == request.values['audio_codec'])

    media = media.order_by(Media.id.desc()).paginate(page, 50)

    stats = {}
    if not request.values:
        stats['video_codecs'] = Media.select(
            fn.COUNT('*').alias('count'),
            Media.video_codec
        ).group_by(Media.video_codec).order_by('count').tuples()

        stats['audio_codecs'] = Media.select(
            fn.COUNT('*').alias('count'),
            Media.audio_codec
        ).group_by(Media.audio_codec).order_by('count').tuples()

    return render_template('media/index.html', media=media, page=page, stats=stats)
