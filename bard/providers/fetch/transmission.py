import json
import requests
import calendar
import datetime
import base64


class UTC(datetime.tzinfo):
    def utcoffset(self, dt):
        return datetime.timedelta(0)

    def tzname(self, dt):
        return 'UTC'

    def dst(self, dt):
        return datetime.timedelta(0)

CSRF_ERROR_CODE = 409
UNAUTHORIZED_ERROR_CODE = 401
CSRF_HEADER = 'X-Transmission-Session-Id'

# UNIX epochs to be turned into UTC datetimes
TIMESTAMP_KEYS = frozenset(
    ['activityDate',
     'addedDate',
     'dateCreated',
     'doneDate',
     'startDate',
     'lastAnnounceStartTime',
     'lastAnnounceTime',
     'lastScrapeStartTime',
     'lastScrapeTime',
     'nextAnnounceTime',
     'nextScrapeTime'])


def epoch_to_datetime(value):
    return datetime.datetime.fromtimestamp(value, UTC())


def datetime_to_epoch(value):
    if isinstance(value, datetime.datetime):
        return calendar.timegm(value.utctimetuple())
    elif isinstance(value, datetime.date):
        value = datetime.datetime(value.year, value.month, value.day)
        return calendar.timegm(value.utctimetuple())


class TransmissionJSONDecoder(json.JSONDecoder):
    def __init__(self, **kwargs):
        return super(TransmissionJSONDecoder, self).__init__(
            object_hook=self.object_hook, **kwargs)

    def object_hook(self, obj):
        for key, value in obj.items():
            if key in TIMESTAMP_KEYS:
                value = epoch_to_datetime(value)
            obj[key] = value
        return obj


class TransmissionJSONEncoder(json.JSONEncoder):
    def default(self, value):
        # datetime is a subclass of date, so this'll catch both
        if isinstance(value, datetime.date):
            return datetime_to_epoch(value)
        else:
            return value


class TransmissionClient(object):
    def __init__(self, url, path='/transmission/rpc',
                 username=None, password=None):
        """
        Initialize the Transmission client.
        The default host, port and path are all set to Transmission's
        default.
        """
        self.url = url + path
        self.headers = {}
        self.tag = 0

        self.auth = None
        if username or password:
            self.auth = (username, password)

    def __call__(self, method, **kwargs):
        """
        Send request to Transmission's RPC interface.
        """
        response = self._make_request(method, **kwargs)
        return self._deserialize_response(response)

    def _make_request(self, method, **kwargs):
        body = json.dumps(self._format_request_body(method, **kwargs), cls=TransmissionJSONEncoder)
        r = requests.post(self.url, data=body, headers=self.headers, auth=self.auth, verify=False)

        if r.status_code == CSRF_ERROR_CODE:
            self.headers[CSRF_HEADER] = r.headers[CSRF_HEADER]
            return self._make_request(method, **kwargs)

        r.raise_for_status()
        return r

    def _format_request_body(self, method, **kwargs):
        """
        Create a request object to be serialized and sent to Transmission.
        """
        fixed = {}
        # As Python can't accept dashes in kwargs keys, replace any
        # underscores with them here.
        for k, v in kwargs.items():
            fixed[k.replace('_', '-')] = v
        return {"method": method, "tag": self.tag, "arguments": fixed}

    def _deserialize_response(self, response):
        """
        Return the response generated by the request object, raising
        BadRequest if there were any problems.
        """
        doc = json.loads(response.text, cls=TransmissionJSONDecoder)

        if doc['result'] != 'success':
            raise Exception('Request failed: `%s`' % doc['result'])

        if doc['tag'] != self.tag:
            raise Exception('Tag mismatch: (got %s expected %s)' % (doc['tag'], self.tag))
        else:
            self.tag += 1

        if 'arguments' in doc:
            return doc['arguments'] or None
        return None


class TransmissionFetchProvider(object):
    STATUS_FIELDS = [
        'hashString',
        'activityDate',
        'addedDate',
        'downloadDir',
        'doneDate',
        'error',
        'errorString',
        'eta',
        'files',
        'fileStats',
        'isFinished',
        'isStalled',
        'peers',
        'percentDone',
        'pieces',
        'secondsDownloading'
    ]

    def __init__(self, bard, opts):
        self.bard = bard
        self.start_paused = opts.pop('start_paused', False)
        self.peer_limit = opts.pop('peer_limit', 500)
        self.client = TransmissionClient(
            opts['url'],
            opts.get('path', '/transmission/rpc'),
            opts.get('username'),
            opts.get('password'),
        )

    def download(self, torrent):
        r = self.client('torrent-add',
                metainfo=base64.b64encode(torrent.raw),
                paused=self.start_paused,
                peer_limit=self.peer_limit)

        if 'torrent-added' in r:
            return r['torrent-added']['hashString']
        elif 'torrent-duplicate' in r:
            return r['torrent-duplicate']['hashString']
        else:
            raise Exception('Failed to add torrent to transmission: {}'.format(r))

    def remove(self, torrent):
        self.client(
                'torrent-remove',
                ids=[torrent.fetch_provider_id],
                delete_local_data=True,
        )

    @staticmethod
    def _get_state_from_info(info):
        from bard.models.torrent import Torrent

        if info['percentDone'] != 1:
            return Torrent.State.DOWNLOADING
        elif info['isFinished']:
            return Torrent.State.COMPLETED
        else:
            return Torrent.State.SEEDING

    def get_torrent_info(self, torrents):
        from bard.providers.fetch import TorrentFetchInfo
        data = self.client('torrent-get', ids=[
            i.fetch_provider_id for i in torrents
        ], fields=self.STATUS_FIELDS)['torrents']

        for item in data:
            yield TorrentFetchInfo(
                id=item['hashString'],
                state=self._get_state_from_info(item),
                done_date=item['doneDate'],
                peers=item['peers'],
                percent_done=item['percentDone'],
                files=[i['name'] for i in item['files']],
            )