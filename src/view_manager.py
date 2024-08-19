import datetime

import discord

from db_manager import Tag, TagManager
from embed_manager import EmbedManager

'''
classらの引数にあるextraは、
extras = {
    (mode: str): (data: any)
    ...
}
のような形式でデータが入っており、関数はそれを参照して処理を行う
'''

tag_manager = TagManager()
embed_manager = EmbedManager()


class ThreadsSelect(discord.ui.ChannelSelect):
    def __init__(self, extras: dict[str, Tag] | None = None):
        '''extrasは基本的に参照されません'''
        super().__init__(
            placeholder='スレッドを選択してください',
            min_values=1,
            max_values=1,
            channel_types=[discord.ChannelType.public_thread, discord.ChannelType.private_thread],
        )
        self.extras = extras
    
    async def callback(self, interaction: discord.Interaction):
        selected_threads = interaction.data['values']
        
        if 'tag' in list(self.extras.keys()):
            self.extras['tag'].thread_id = selected_threads[0]
            await interaction.response.edit_message(
                view=TagView2(extras=self.extras),
                embed=embed_manager.get_embed(self.extras)
            )
        
        elif 'untag' in list(self.extras.keys()):
            self.extras['untag'].thread_id = selected_threads[0]
            # 現在タグ付けされているユーザーを表示するための処理
            tagged_user_ids = tag_manager.get_users_by_thread(self.extras['untag'])
            self.extras['untag_tagged_user_ids'] = tagged_user_ids
            await interaction.response.edit_message(
                view=UntagView2(extras=self.extras),
                embed=embed_manager.get_embed(self.extras)
            )
        
        elif 'get_users_by_thread' in list(self.extras.keys()):
            thread = self.extras['get_users_by_thread'].client.get_channel(int(selected_threads[0]))
            self.extras['get_users_by_thread'].thread_id = thread.id
            self.extras['get_users_by_thread'].guild_id = thread.guild.id
            users = tag_manager.get_users_by_thread(self.extras['get_users_by_thread'])
            
            self.extras['result'] = {'get_users_by_thread': {'thread': thread, 'users': users}}
            
            await interaction.response.edit_message(
                view=None,
                embed=embed_manager.get_embed(self.extras)
            )

class MemberSelect(discord.ui.UserSelect):
    def __init__(self, extras: dict[str, Tag] | None = None):
        '''
        extrasは、tag,untagモードの場合は
        {
            'tag': Tag(),
        }
        のようになっている必要があります
        
        '''
        super().__init__(
            placeholder='ユーザーを選択してください',
            min_values=1,
            max_values=25,
        )
        self.extras = extras
    
    async def callback(self, interaction: discord.Interaction):
        selected_user_ids = interaction.data['values']
        
        if 'tag' in list(self.extras.keys()):
            user_ids = selected_user_ids
            users = [self.extras['tag'].client.get_user(int(user_id)) for user_id in user_ids]
            self.extras['tag'].users = users
            await interaction.response.send_modal(DeadlineInputModal(extras=self.extras))
        
        elif 'untag' in list(self.extras.keys()):
            user_ids = selected_user_ids
            users = [self.extras['untag'].client.get_user(int(user_id)) for user_id in user_ids]
            self.extras['untag'].users = users
            tag_manager.remove_tag(self.extras['untag'])
            await interaction.response.edit_message(
                view=None,
                embed=embed_manager.get_embed(self.extras)
            )
        
        elif 'get_threads_by_user' in list(self.extras.keys()):
            selected_users = [self.extras['get_threads_by_user'].client.get_user(int(user_id)) for user_id in selected_user_ids]
            self.extras['get_threads_by_user'].users = selected_users
            result = {'get_threads_by_user': []}
            for user in selected_users:
                thread_infos = tag_manager.get_threads_by_user([user])
                current_guild = interaction.guild
                # interactionのguild以外のguild配下のスレッドを除外する
                for guild_id in list(thread_infos.keys()):
                    if int(guild_id) != current_guild.id:
                        del thread_infos[guild_id]
                
                if str(current_guild.id) not in list(thread_infos.keys()):
                    continue
                
                # tupleで返ってきたデータをdictに変換 
                dicted_threads = []
                for thread_data in thread_infos[str(current_guild.id)]:
                    thread_id, deadline = thread_data
                    thread = self.extras['get_threads_by_user'].client.get_channel(int(thread_id))
                    dicted_threads.append({'thread': thread, 'deadline': deadline})
                
                result['get_threads_by_user'].append({'user': user, 'threads': dicted_threads})
            
            self.extras['result'] = result
            await interaction.response.edit_message(
                view=None,
                embed=embed_manager.get_embed(self.extras)
            )

class DeadlineInputModal(discord.ui.Modal):
    raw_deadline = discord.ui.TextInput(
        placeholder='例: 2020-01-01',
        label='期限',
        style=discord.TextStyle.short,
        min_length=1,
        max_length=3900,
    )
    
    def __init__(self, extras: dict[str, Tag] | None = None):
        super().__init__(title='3/3 期限の入力')
        self.extras = extras
    
    async def on_submit(self, interaction: discord.Interaction):
        deadline = self.raw_deadline.value
        
        if 'tag' in list(self.extras.keys()):
            deadline = datetime.datetime.strptime(deadline, '%Y-%m-%d')
            self.extras['tag'].deadline = deadline
            tag_manager.add_tag(self.extras['tag'])
            await interaction.response.edit_message(
                view=None,
                embed=embed_manager.get_embed(self.extras)
            )
        


class ConfimButton(discord.ui.Button):
    def __init__(self, extras: dict[str, Tag] | None = None):
        super().__init__(
            label='OK',
            style=discord.ButtonStyle.primary,
        )
        self.extras = extras
    
    async def callback(self, interaction: discord.Interaction):
        pass

class CancelButton(discord.ui.Button):
    def __init__(self, extras: dict[str, Tag] | None = None):
        super().__init__(
            label='キャンセル',
            style=discord.ButtonStyle.secondary,
        )
        self.extras = extras
    
    async def callback(self, interaction: discord.Interaction):
        self.extras = {'cancel': None}
        await interaction.response.edit_message(view=None, embed=embed_manager.get_embed(self.extras))


########## tag ##########
class TagView1(discord.ui.View):
    def __init__(self, extras: dict[str, Tag] | None = None):
        super().__init__()
        self.add_item(ThreadsSelect(extras=extras))
        self.add_item(CancelButton(extras=extras))

class TagView2(discord.ui.View):
    def __init__(self, extras: dict[str, Tag] | None = None):
        super().__init__()
        self.add_item(MemberSelect(extras=extras))
        self.add_item(CancelButton(extras=extras))


########## untag ##########
class UntagView1(discord.ui.View):
    def __init__(self, extras: dict[str, Tag] | None = None):
        super().__init__()
        self.add_item(ThreadsSelect(extras=extras))
        self.add_item(CancelButton(extras=extras))

class UntagView2(discord.ui.View):
    def __init__(self, extras: dict[str, Tag] | None = None):
        super().__init__()
        self.add_item(MemberSelect(extras=extras))
        self.add_item(CancelButton(extras=extras))

########## get_threads_by_user ##########
class GetThreadsView1(discord.ui.View):
    def __init__(self, extras: dict[str, Tag] | None = None):
        super().__init__()
        self.add_item(MemberSelect(extras=extras))
        self.add_item(CancelButton(extras=extras))


########## get_users_by_thread ##########
class GetUsersView1(discord.ui.View):
    def __init__(self, extras: dict[str, Tag] | None = None):
        super().__init__()
        self.add_item(ThreadsSelect(extras=extras))
        self.add_item(CancelButton(extras=extras))
