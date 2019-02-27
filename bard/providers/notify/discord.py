from .base import BaseNotifyProvider

from disco.types.webhook import Webhook


class DiscordNotifyProvider(BaseNotifyProvider):
    def execute(self, **kwargs):
        return Webhook.execute_url(self.opts['url'], **kwargs)

    def episode_downloaded(self, episode):
        self.execute(content='Finished downloading %s' % episode.to_string())
