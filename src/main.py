import asyncio
from dataclasses import dataclass
import datetime
import os

import discord
from discord import app_commands
from discord.ext import tasks
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore

from db_manager import TagManager
from notification_handler import NotificationHandler
from view_manager import TagView1


intents = discord.Intents.all()

class Client(discord.Client):
    def __init__(self):
        super().__init__(intents=intents)
        self.synced = False
        self.tag_manager = TagManager()
        self.notification_handler = NotificationHandler(self)
    
    ########## discord.py events ##########
    
    async def on_ready(self):
        # treeコマンドを同期
        if not self.synced:
            await self.sync_commands()
        
        guilds = self.guilds
        # ギルドメンバーを同期
        await self.guild_member_sync(guilds)
        
        print('Bot is ready.')
        
        # 毎日0時に通知
        until_notify = await self.calc_until_notify()
        await asyncio.sleep(until_notify)
        self.notify.start()
    
    async def on_guild_join(self, guild: discord.Guild):
        # ギルドメンバーを同期
        await self.guild_member_sync([guild])
    
    ########## my functions ##########
    
    async def sync_commands(self):
        if self.synced:
            return
        # treeコマンドを同期
        await tree.sync()
        print('Commands synced.')
        self.synced = True
        return
    
    async def guild_member_sync(self, guilds: list[discord.Guild]):
        all_members = []
        
        for guild in guilds:
            # ギルドメンバーを取得してタグマネージャーにセット
            guild_members = guild.fetch_members(limit=None)
            guild_members = [member async for member in guild_members if not member.bot]
            all_members.extend(guild_members)
        
        # memberのidからMemberをUserに変換してタグマネージャーにセット
        self.tag_manager.set_users([self.get_user(member.id) for member in all_members])
    
    async def calc_until_notify(self) -> float:
        tz = datetime.timezone(datetime.timedelta(hours=9)) # JST
        today = datetime.datetime.now(tz).date()
        now = datetime.datetime.now(tz)
        midnight = datetime.datetime.combine(today, datetime.time(0, 0, 0, 0), tz)
        until_notify = midnight + datetime.timedelta(days=1) - now # 今日の0時からの残り時間
        total_seconds = until_notify.total_seconds()
        return total_seconds
    
    ########## notify ##########
    notify_freq = 24 # 通知頻度(時間)
    @tasks.loop(hours=notify_freq)
    async def notify(self):
        # 通知を送信
        threads = self.tag_manager.get_all_guilds()
        guilds = self.guilds
        for guild in guilds:
            threads = guild.threads
            for thread in threads:
                await self.notification_handler.send_notification_to_thread(guild.id, thread.id)
        return


client = Client()
tree = discord.app_commands.CommandTree(client)


@dataclass
class Tag:
    guild_id: int = None
    thread_id: int = None
    users: list[discord.User] = None
    deadline: datetime.datetime = None


@tree.command(name='ping', description='for testng')
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message('pong')

@tree.command(name='change_notify_freq', description='通知頻度を変更します')
async def change_notify_freq(interaction: discord.Interaction):
    pass

@tree.command(name='tag', description='ユーザーを指定したスレッドにタグ付けします')
async def tag(interaction: discord.Interaction):
    await interaction.response.send_message(view=TagView1())
    async def tag_callback(interaction: discord.Interaction, selected_thread: discord.Thread, selected_users: list[discord.User]):
        # これをview_managerから呼び出して、ここで処理を書く
        pass

@tree.command(name='untag', description='ユーザーからタグ付けを解除します')
async def untag(interaction: discord.Interaction):
    await interaction.response.send_message(view=UntagView1())
    async def untag_callback(interaction: discord.Interaction, selected_thread: discord.Thread, selected_users: list[discord.User]):
        # これをview_managerから呼び出して、ここで処理を書く
        pass

@tree.command(name='get_threads_by_user', description='指定したユーザーがタグ付けされているスレッドを取得します')
async def get_threads_by_user(interaction: discord.Interaction):
    await interaction.response.send_message(view=GetThreadsView1())
    async def get_threads_callback(interaction: discord.Interaction, selected_user: discord.User):
        # これをview_managerから呼び出して、ここで処理を書く
        pass

@tree.command(name='get_users_by_thread', description='指定したスレッドにタグ付けされているユーザーを取得します')
async def get_users_by_thread(interaction: discord.Interaction):
    await interaction.response.send_message(view=GetUsersView1())
    async def get_users_callback(interaction: discord.Interaction, selected_thread: discord.Thread):
        # これをview_managerから呼び出して、ここで処理を書く
        pass

@tree.command(name='get_all', description='全てのタグを取得します')
async def get_all(interaction: discord.Interaction):
    await interaction.response.send_message(view=GetAllView1())
    async def get_all_callback(interaction: discord.Interaction):
        # これをview_managerから呼び出して、ここで処理を書く
        pass

@tree.command(name='toggle_notification', description='通知のON/OFFを切り替えます')
async def toggle_notification(interaction: discord.Interaction):
    await interaction.response.send_message(view=ToggleNotificationView1())
    async def toggle_notification_callback(interaction: discord.Interaction):
        # これをview_managerから呼び出して、ここで処理を書く
        pass

@tree.command(name='help', description='ヘルプを表示します')
async def help(interaction: discord.Interaction):
    await interaction.response.send_message(view=HelpView1())
    async def help_callback(interaction: discord.Interaction):
        # これをview_managerから呼び出して、ここで処理を書く
        pass

@tree.command(name='invite_link', description='招待リンクを表示します')
async def invite_link(interaction: discord.Interaction):
    await interaction.response.send_message(view=InviteLinkView1())
    async def invite_link_callback(interaction: discord.Interaction):
        # これをview_managerから呼び出して、ここで処理を書く
        pass


if __name__ == '__main__':
    client.run(os.getenv('DISCORD_BOT_TOKEN_MT'))
