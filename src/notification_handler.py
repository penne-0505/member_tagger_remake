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
    
    async def send_notification_to_thread(self, guild_id: int, thread_id: int):
        user_ids = self.client.tag_manager.get_users_by_thread(guild_id, thread_id) # not best practice :(

        deadline = self.client.tag_manager.get_threads(user_ids[0])[thread_id]
        until_deadline = deadline - datetime.datetime.now().date()
        message = discord.Embed(
            title=f'期限まであと{until_deadline}日です',
            description=str([self.client.get_user(user_id).mention for user_id in user_ids])
        )
        
        target_thread = self.client.get_guild(guild_id).get_channel_or_thread(thread_id)
        await target_thread.send(embed=message)