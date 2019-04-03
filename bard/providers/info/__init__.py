from .tvdb import TVDBInfoProvider
from .tmdb import TMDBInfoProvider

PROVIDERS = {
    'tvdb': TVDBInfoProvider,
    'tmdb': TMDBInfoProvider,
}
