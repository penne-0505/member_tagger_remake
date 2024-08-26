import datetime

import discord

from db_manager import TagManager
from embed_manager import EmbedManager
from utils import Tag, Task

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
        
        elif 'add_task' in list(self.extras.keys()):
            user_ids = selected_user_ids
            users = [self.extras['add_task'].client.get_user(int(user_id)) for user_id in user_ids]
            self.extras['add_task'].users = users
            await interaction.response.send_modal(TaskContentInputModal(extras=self.extras))

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
        
        elif 'add_task' in list(self.extras.keys()):
            deadline = datetime.datetime.strptime(deadline, '%Y-%m-%d')
            self.extras['add_task'].deadline = deadline
            await interaction.response.send_message(
                view=None,
                embed=embed_manager.get_embed(self.extras)
            )

class TaskContentInputModal(discord.ui.Modal):
    raw_content = discord.ui.TextInput(
        placeholder='タスクの内容を入力してください',
        label='内容',
        style=discord.TextStyle.long,
        min_length=1,
        max_length=3900,
    )
    
    def __init__(self, extras: dict[str, Task] | None = None):
        super().__init__(title='あなたに紐づけるタスクの内容の入力')
        self.extras = extras
    
    async def on_submit(self, interaction: discord.Interaction):
        content = str(self.raw_content.value)
        
        if 'add_task' in list(self.extras.keys()):
            self.extras['add_task'].content = content

            tag_manager.add_task(self.extras['add_task'])
            await interaction.response.send_message(
                ephemeral=True,
                embed=embed_manager.get_embed(self.extras)
            )

class TaskSelect(discord.ui.Select):
    def __init__(self, extras: dict[str, Task | list[Task]] | None = None):
        self.extras = extras
        current_page = self.extras['result']['current_page']
        tasks_per_page = 25
        start_index = (current_page - 1) * tasks_per_page
        end_index = start_index + tasks_per_page
        # ページング処理
        tasks = list(self.extras['result']['delete_task'].items())[start_index:end_index]
        
        if not tasks:
            # データが存在しない場合は最後尾のデータを表示
            total_tasks = len(self.extras['result']['delete_task'])
            last_page = (total_tasks - 1) // tasks_per_page + 1
            start_index = (last_page - 1) * tasks_per_page
            end_index = start_index + tasks_per_page
            tasks = list(self.extras['result']['delete_task'].items())[start_index:end_index]
        
        select_options = []
        user = self.extras['delete_task'].user
        for task in tasks:
            option = (discord.SelectOption(
            label=task[1],
            value=task[0],
            ))
            select_options.append(option)
        
        values_len = len(select_options) if len(select_options) < 25 else 25
        
        super().__init__(
            placeholder=f'{user}のタスクを選択してください',
            min_values=1,
            max_values=values_len,
            options=select_options if len(select_options) < 25 else select_options[:25],
        )
        
        self.extras = extras
    
    async def callback(self, interaction: discord.Interaction):
        selected_task_ids = interaction.data['values']
        
        if 'delete_task' in list(self.extras.keys()):
            for task_id in selected_task_ids:
                self.extras['delete_task'].task_id = task_id
                tag_manager.delete_task(self.extras['delete_task'])
            
            self.extras['result'] = {'delete_task': 'done'}
            
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
        await interaction.response.edit_message(
            view=None,
            embed=embed_manager.get_embed(self.extras)
        )

# これはdelete_taskのviewで、taskが25個以上ある場合に次のページを表示するためのボタン
class NextPageButton(discord.ui.Button):
    def __init__(self, extras: dict[str, Tag | Task] | None = None):
        super().__init__(
            label='次のページ',
            style=discord.ButtonStyle.primary,
        )
        self.extras = extras
    
    async def callback(self, interaction: discord.Interaction):
        self.extras['result']['current_page'] += 1
        
        # ページが25ページを超える場合は25ページ目に戻す
        if self.extras['result']['current_page'] > 25:
            self.extras['result']['current_page'] = 25
        # pageを超えるcurrent_pageが指定された場合はpageに戻す
        elif self.extras['result']['current_page'] > self.extras['result']['page']:
            self.extras['result']['current_page'] = self.extras['result']['page']
        
        view = DeleteTaskViewNext if self.extras['result']['current_page'] != self.extras['result']['page'] else DeleteTaskViewOnly
        
        await interaction.response.edit_message(
            view=view(extras=self.extras),
            embed=embed_manager.get_embed(self.extras)
        )

class PreviousPageButton(discord.ui.Button):
    def __init__(self, extras: dict[str, Tag | Task] | None = None):
        super().__init__(
            label='前のページ',
            style=discord.ButtonStyle.primary,
        )
        self.extras = extras
    
    async def callback(self, interaction: discord.Interaction):
        self.extras['result']['current_page'] -= 1
        
        if self.extras['result']['current_page'] < 1:
            self.extras['result']['current_page'] = 1
        
        view = DeleteTaskViewAll if self.extras['result']['current_page'] != 1 else DeleteTaskViewPrev
        
        await interaction.response.edit_message(
            view=view(extras=self.extras),
            embed=embed_manager.get_embed(self.extras)
        )

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


########## delete_task ##########
class DeleteTaskViewAll(discord.ui.View):
    def __init__(self, extras: dict[str, Tag] | None = None):
        super().__init__()
        self.add_item(TaskSelect(extras=extras))
        self.add_item(PreviousPageButton(extras=extras))
        self.add_item(NextPageButton(extras=extras))
        self.add_item(CancelButton(extras=extras))

class DeleteTaskViewPrev(discord.ui.View):
    def __init__(self, extras: dict[str, Tag] | None = None):
        super().__init__()
        self.add_item(TaskSelect(extras=extras))
        self.add_item(PreviousPageButton(extras=extras))
        self.add_item(CancelButton(extras=extras))

class DeleteTaskViewNext(discord.ui.View):
    def __init__(self, extras: dict[str, Tag] | None = None):
        super().__init__()
        self.add_item(TaskSelect(extras=extras))
        self.add_item(NextPageButton(extras=extras))
        self.add_item(CancelButton(extras=extras))

class DeleteTaskViewOnly(discord.ui.View):
    def __init__(self, extras: dict[str, Tag] | None = None):
        super().__init__()
        self.add_item(TaskSelect(extras=extras))
        self.add_item(CancelButton(extras=extras))

########## get_tasks_by_user ##########
class GetTasksView1(discord.ui.View):
    def __init__(self, extras: dict[str, Tag] | None = None):
        super().__init__()
        self.add_item(MemberSelect(extras=extras))
        self.add_item(CancelButton(extras=extras))
