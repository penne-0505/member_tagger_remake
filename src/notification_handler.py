import asyncio
import datetime

import discord


class NotificationHandler:
    def __init__(self, client: discord.Client):
        self.client = client

    ####### low level funcs #######
    
    async def send_notification(self, guild_id: int, thread_id: list[int], message: str):
        # guildとchannelを取得してメッセージを送信
        guild = self.client.get_guild(guild_id)
        for thread_id in thread_id:
            channel = guild.get_channel(thread_id)
            await channel.send(message)
    
    async def send_notification_to_users(self, user_ids: list[int], message: str):
        for user_id in user_ids:
            user = self.client.get_user(user_id)
            await user.send(message) # DMで送信
    
    ####### high level funcs #######
    
    async def send_notification_to_all(self):
        all_user_ids = self.client.tag_manager.get_all_users()
        all_users = [self.client.get_user(user_id) for user_id in all_user_ids]
        threads = self.client.tag_manager.get_threads_by_user(all_users)
        for guild_id in threads:
            # TODO: send_notificationで送信
            pass