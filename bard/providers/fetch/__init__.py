from collections import namedtuple
from .transmission import TransmissionFetchProvider


PROVIDERS = {
    'transmission': TransmissionFetchProvider,
}

TorrentFetchInfo = namedtuple('TorrentFetchInfo', (
    'id',
    'state',
    'done_date',
    'peers',
    'percent_done',
    'files',
))
