from .tvdb import TVDBInfoProvider
from .tmdb import TMDBInfoProvider

INFO_PROVIDERS = {
    'tvdb': TVDBInfoProvider,
    'tmdb': TMDBInfoProvider,
}
