import asyncio
import datetime
import logging
from os import getenv

import discord
from discord import app_commands
from discord.ext import tasks

from db_manager import TagManager, Tag
from embed_manager import EmbedManager
from notification_handler import NotificationHandler
from view_manager import TagView1, UntagView1, GetThreadsView1, GetUsersView1
from utils import INFO, ERROR, WARN, DEBUG, SUCCESS, FORMAT, DATEFORMAT, blue, red, yellow, magenta, green, cyan, bold


# intents(権限のようなもの)を全て有効化
intents = discord.Intents.all()

logging.basicConfig(level=logging.INFO, format=FORMAT, datefmt=DATEFORMAT)


class Client(discord.Client):
    def __init__(self):
        super().__init__(intents=intents)
        self.synced = False
        self.tag_manager = TagManager()
        self.embed_manager = EmbedManager()
        self.notification_handler = NotificationHandler(self)
    
    ########## discord.py events ##########
    
    async def on_ready(self):
        # treeコマンドを同期
        if not self.synced:
            await self.sync_commands()
        
        guilds = self.guilds
        # ギルドメンバーを同期
        await self.guild_member_sync(guilds)
        
        self.set_presence.start()
        
        # logging
        logging.info(INFO + f'Logged in as {self.user.name}({self.user.id})')
        logging.info(INFO + f'Bot is ready.')
        
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
        logging.info(SUCCESS + 'Commands synced.')
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
        current_users_raw = self.tag_manager.get_all_users()
        current_users_id = [user['user_id'] for user in current_users_raw]
        current_users = [self.get_user(user_id) for user_id in current_users_id]
        all_members = [self.get_user(member.id) for member in all_members]
        target_users = [member for member in all_members if member not in current_users]

        # logging
        msg = INFO + 'New users: ' + ', '.join([user.name for user in target_users]) if target_users else INFO + 'No new users.'
        logging.info(msg)

        # タグマネージャーにセット
        for user in target_users:
            self.tag_manager.add_user(user)
    
    # 通知までの時間を計算
    async def calc_until_notify(self) -> float:
        tz = datetime.timezone(datetime.timedelta(hours=9)) # JST
        today = datetime.datetime.now(tz).date()
        now = datetime.datetime.now(tz)
        midnight = datetime.datetime.combine(today, datetime.time(0, 0, 0, 0), tz)
        until_notify = midnight + datetime.timedelta(days=1) - now # 今日の0時からの残り時間
        total_seconds = until_notify.total_seconds()
        logging.info(INFO + f'Until notify: {int(total_seconds)}seconds')
        return total_seconds

    # コマンド実行時のログ
    async def on_app_command_completion(self, interaction: discord.Interaction, command: app_commands.Command | app_commands.ContextMenu):
        # 装飾してログを出力
        exec_time = magenta(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        exec_user = interaction.user
        user_name = blue(exec_user.name)
        user_id = blue(exec_user.id)
        exec_command = green(command.name)
        logging.info(INFO + f'Command executed by {user_name}({user_id}): {exec_command} at {exec_time}')
    
    # 30分ごとにプレゼンスを更新
    @tasks.loop(minutes=30)
    async def set_presence(self):
        now = datetime.datetime.now()
        now = now.strftime('%Y/%m/%d %H:%M') # 例: 2021/08/01 12:34
        activity = discord.Game(name=f'/help | {now}')
        await self.change_presence(activity=activity)
        await tree.sync()
        logging.info(INFO + 'Presence set at ' + now)
    
    ########## notify ##########
    notify_freq = 24 # 通知頻度(時間) (将来的にはdiscord上で変更できるようにする(?))
    @tasks.loop(hours=notify_freq)
    async def notify(self):
        # すべてのユーザー、スレッド、期限を取得して、通知を送る
        for user in self.tag_manager.get_all_users():
            user_obj = self.get_user(user['user_id'])
            if not user_obj:
                continue
            
            threads = self.tag_manager.get_threads_by_user([user_obj])
            for guild_id in list(threads.keys()):
                guild = self.get_guild(int(guild_id))
                if not guild:
                    continue
                
                for thread_data in threads[guild_id]:
                    thread_id, deadline = thread_data
                    thread = guild.get_channel(int(thread_id))
                    if not thread:
                        continue
                    
                    await self.notification_handler.send_notification(user_obj, thread, deadline)
        
        return


client = Client()
tree = discord.app_commands.CommandTree(client)


@tree.command(name='ping', description='for testing')
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message('pong! 🏓', ephemeral=True)

@tree.command(name='change_notify_freq', description='通知頻度を変更します')
async def change_notify_freq(interaction: discord.Interaction):
    await interaction.response.send_message('このコマンドは未実装です', ephemeral=True)

@tree.command(name='tag', description='ユーザーを指定したスレッドにタグ付けします')
async def tag(interaction: discord.Interaction):
    extras = {'tag': Tag(client=client, guild_id=interaction.guild_id)}
    await interaction.response.send_message(
        ephemeral=True,
        view=TagView1(extras=extras),
        embed=client.embed_manager.get_embed(extras)
    )

@tree.command(name='untag', description='ユーザーからタグ付けを解除します')
async def untag(interaction: discord.Interaction):
    extras = {'untag': Tag(client=client, guild_id=interaction.guild_id)}
    await interaction.response.send_message(
        ephemeral=True,
        view=UntagView1(extras=extras),
        embed=client.embed_manager.get_embed(extras)
    )

@tree.command(name='get_threads_by_user', description='指定したユーザーがタグ付けされているスレッドを取得します')
async def get_threads_by_user(interaction: discord.Interaction):
    extras = {'get_threads_by_user': Tag(client=client)}
    await interaction.response.send_message(
        ephemeral=True,
        view=GetThreadsView1(extras=extras),
        embed=client.embed_manager.get_embed(extras)
    )

@tree.command(name='get_users_by_thread', description='指定したスレッドにタグ付けされているユーザーを取得します')
async def get_users_by_thread(interaction: discord.Interaction):
    extras = {'get_users_by_thread': Tag(client=client)}
    await interaction.response.send_message(
        ephemeral=True,
        view=GetUsersView1(extras=extras),
        embed=client.embed_manager.get_embed(extras)
    )

@tree.command(name='get_all', description='全てのタグを取得します')
async def get_all(interaction: discord.Interaction):
    '''
    sample data
    [{'notification': True, 'user_id': 1021394941743734814, 'tasks': {}, 'tags': {}, 'name': 'mamadaisuki.'}, {'notification': True, 'user_id': 1038733998630899743, 'tasks': {}, 'tags': {}, 'name': 'error.428'}, {'notification': True, 'user_id': 569651149440024628, 'tasks': {}, 'tags': {}, 'name': 'onigiri_oo'}, {'notification': True, 'user_id': 641764833460748295, 'tasks': {}, 'tags': {}, 'name': 'chongyanjing8744'}, {'notification': True, 'user_id': 687202120969355284, 'tasks': {}, 'tags': {}, 'name': 'zapks'}, {'notification': True, 'user_id': 704115683151315055, 'tasks': {}, 'tags': {'1039814831395569676': {'1270798541970739200': DatetimeWithNanoseconds(2020, 1, 1, 0, 0, tzinfo=datetime.timezone.utc)}, '884682745429766164': {'1272926429960732763': DatetimeWithNanoseconds(2024, 8, 13, 0, 0, tzinfo=datetime.timezone.utc), '1212549118929543248': DatetimeWithNanoseconds(2024, 8, 15, 0, 0, tzinfo=datetime.timezone.utc)}}, 'name': 'penne0505'}, {'notification': True, 'user_id': 711421164194365471, 'tasks': {}, 'tags': {}, 'name': 'rarorurerin'}, {'notification': True, 'user_id': 712503770931527778, 'tasks': {}, 'tags': {}, 'name': 'piplup_lv.5'}, {'notification': True, 'user_id': 720241890662023268, 'tasks': {}, 'tags': {}, 'name': 'sasasasawamura'}, {'notification': True, 'user_id': 730778811263746062, 'tasks': {}, 'tags': {}, 'name': 'aoi053112'}, {'notification': True, 'user_id': 744469461750382714, 'tasks': {}, 'tags': {}, 'name': 'sokusi9929'}, {'notification': True, 'user_id': 756101891548512287, 'tasks': {}, 'tags': {}, 'name': 'fookurou'}, {'notification': True, 'user_id': 824616112909058058, 'tasks': {}, 'tags': {}, 'name': 'yamamoto_katsuyoshi'}, {'notification': True, 'user_id': 843146360244011008, 'tasks': {}, 'tags': {}, 'name': 'aki5672'}, {'notification': True, 'user_id': 867192594962055178, 'tasks': {}, 'tags': {}, 'name': 'tarabaebi'}, {'notification': True, 'user_id': 886465290785918996, 'tasks': {}, 'tags': {}, 'name': 'fukimayu'}, {'notification': True, 'user_id': 907286924354551829, 'tasks': {}, 'tags': {}, 'name': 'testbot.'}, {'notification': True, 'user_id': 912553432093712434, 'tasks': {}, 'tags': {}, 'name': 'tarabagai_ebi'}, {'notification': True, 'user_id': 938704672905105439, 'tasks': {}, 'tags': {}, 'name': 'obzerver381ribenrendesu9041'}, {'notification': True, 'user_id': 948937635806707762, 'tasks': {}, 'tags': {}, 'name': 'xizhuzhenshu7946'}, {'notification': True, 'user_id': 957815990425624596, 'tasks': {}, 'tags': {}, 'name': 'yutsukurishikuangebichiyanneru'}, {'notification': True, 'user_id': 958492903217451069, 'tasks': {}, 'tags': {}, 'name': 'f.ka0311'}, {'notification': True, 'user_id': 966630541950586900, 'tasks': {}, 'tags': {}, 'name': 'mont7465'}, {'notification': True, 'user_id': 972763598625574995, 'tasks': {}, 'tags': {}, 'name': 'kyohakarakuti'}]
    process data like: [{discord.User: [discord.Thread, ...]}, ...]
    '''
    result = []
    for user in client.tag_manager.get_all_users():
        
        user_obj = client.get_user(user['user_id'])
        if not user_obj:
            continue
        
        threads = client.tag_manager.get_threads_by_user([user_obj])
        
        result.append({user_obj: threads})
    
    extras = {'get_all': Tag(client=client), 'result': {'get_all': result, 'interaction': interaction}}
    await interaction.response.send_message(
        ephemeral=True,
        embed=client.embed_manager.get_embed(extras)
    )

@tree.command(name='toggle_notification', description='通知のON/OFFを切り替えます')
async def toggle_notification(interaction: discord.Interaction):
    current_notification = client.tag_manager.toggle_notification(interaction.user)
    extras = {'toggle_notification': Tag(client=client), 'current_notification': current_notification}
    await interaction.response.send_message(
        ephemeral=True,
        embed=client.embed_manager.get_embed(extras)
    )

# @tree.command(name='help', description='ヘルプを表示します')
# async def help(interaction: discord.Interaction):
#     await interaction.response.send_message(ephemeral=True, view=HelpView1())

# @tree.command(name='invite_link', description='招待リンクを表示します')
# async def invite_link(interaction: discord.Interaction):
#     await interaction.response.send_message(ephemeral=True, view=InviteLinkView1())


if __name__ == '__main__':
    client.run(getenv('DISCORD_BOT_TOKEN_MT'))
