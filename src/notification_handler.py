# notification_handler.py: 

import asyncio
import datetime
from dataclasses import dataclass

import discord

from db_manager import Tag


channel_schema = dict[discord.Guild, discord.TextChannel | discord.Thread | None]

# ここまで小規模な処理にdataclassを使う必要はないかもしれませんが、内容の不明瞭なdictを使いたくないので使っています
@dataclass
class Notification:
    client: discord.Client
    interaction: discord.Interaction | None
    send_to_ch: channel_schema
    message: str | None
    target_tags: list[Tag]


class NotificationHandler:
    def __init__(self, client: discord.Client):
        self.client = client
    
    async def format_db_data(
        self,
        data: list[dict[discord.User, dict[str, list[tuple[str | datetime.datetime]]]]],
        notification_data: Notification | None = None
    ):
        '''
        data such as [{user: {guild_id(str): [(thread_id(str), deadline(datetime.datetime)) ...], ...}, ...]
        formatted_data such as [{guild: [Tag, Tag, ...], ...}, ...]
        '''
        formatted_data = []

        for user_data in data:
            for user, threads in user_data.items():
                for guild_id, thread_data in threads.items():
                    guild = self.client.get_guild(int(guild_id)) # 存在の確認のための変換
                    if not guild:
                        continue

                    guild_data = {guild: []}
                    for thread_id, deadline in thread_data:
                        thread = guild.get_thread(int(thread_id)) # 存在の確認のための変換
                        if not thread:
                            continue

                        tag = Tag(
                            client=self.client,
                            guild_id=guild_id,
                            thread_id=thread_id,
                            deadline=deadline,
                            users=[user]
                        )
                        guild_data[guild].append(tag)
                    
                    formatted_data.append(guild_data)

        return formatted_data


    async def send_notification(self, notification_data: Notification):
        # 全ユーザーを取得 -> ユーザーごとにスレッドを取得(全ユーザーの全タグを取得) -> データを整形
        all_users = notification_data.client.tag_manager.get_all_users()
        result = []
        
        for user in all_users:

            user_obj = notification_data.client.get_user(user['user_id'])
            
            if not user_obj:
                continue
            
            threads = notification_data.client.tag_manager.get_threads_by_user([user_obj])
            result.append({user_obj: threads})
        
        # データを整形
        formatted_data = await self.format_db_data(result)
        
        # guildごとに通知を送る。ギルドごとにデータを丸ごとembed_managerに渡して、embedを作成してもらう
        for guild_data in formatted_data:
            
            tags = guild_data[list(guild_data.keys())[0]]
            
            result = {'notification': tags, 'result': {'notification': tags}} # 超冗長だけど他の処理に合わせるためにこうしています
            embed = notification_data.client.embed_manager.get_embed(result)
            
            # 通知先のチャンネルを取得
            channel = notification_data.send_to_ch[list(guild_data.keys())[0]] if list(guild_data.keys())[0] in notification_data.send_to_ch else None
            
            await channel.send(embed=embed) if channel else None
        
        return formatted_data # 通知したデータを返す