from .base import BaseNotifyProvider

from disco.types.webhook import Webhook
from disco.types.message import MessageEmbed


class DiscordNotifyProvider(BaseNotifyProvider):
    def execute(self, **kwargs):
        return Webhook.execute_url(self.opts['url'], **kwargs)

    def episodes_downloaded(self, episodes):
        if len(episodes) > 3:
            self._send_bulk_episodes_notification(episodes)
        else:
            for episode in episodes:
                self._send_episode_notification(episode)

    def _send_episode_notification(self, episode):
        embed = MessageEmbed()
        embed.color = 0x77dd77
        embed.title = '{0.series.name} {0.season_episode_id} is now available'.format(episode)
        embed.description = episode.desc
        self.execute(embeds=[embed])

    def _send_bulk_episodes_notification(self, episodes):
        embed = MessageEmbed()
        embed.color = 0x77dd77
        embed.title = '{count} new episodes of {series.name} are available'.format(
            count=len(episodes),
            series=episodes[0].series,
        )
        embed.description = '\n'.join(
            ('- ' + i.season_episode_id) for i in episodes
        )
        self.execute(embeds=[embed])
