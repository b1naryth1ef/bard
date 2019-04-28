from .iptorrents import IPTorrentsDownloadProvider
from .horriblesubs import HorribleSubsDownloadProvider

PROVIDERS = {
    'iptorrents': IPTorrentsDownloadProvider,
    'horriblesubs': HorribleSubsDownloadProvider,
}
