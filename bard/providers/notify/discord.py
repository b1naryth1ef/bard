from .base import BaseNotifyProvider

from disco.types.webhook import Webhook
from disco.types.message import MessageEmbed


class DiscordNotifyProvider(BaseNotifyProvider):
    def execute(self, **kwargs):
        return Webhook.execute_url(self.opts['url'], **kwargs)

    def episode_downloaded(self, episode):
        embed = MessageEmbed()
        embed.color = 0x77dd77
        embed.title = '{0.series.name} {0.season_episode_id} is now available'.format(episode)
        embed.description = episode.desc
        self.execute(embeds=[embed])
