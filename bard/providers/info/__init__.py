from .tvdb import TVDBInfoProvider
from .tmdb import TMDBInfoProvider
from .tvmaze import TVMazeInfoProvider

PROVIDERS = {
    'tvdb': TVDBInfoProvider,
    'tmdb': TMDBInfoProvider,
    'tvmaze': TVMazeInfoProvider,
}
