import discord

from main import Tag, client

'''
classらの引数にあるextraは、
extras = {
    (mode: str): (data: any)
    ...
}
のような形式でデータが入っており、関数はそれを参照して処理を行う
'''

class ThreadsSelect(discord.ui.ChannelSelect):
    def __init__(self, extras: dict | None = None):
        '''extrasは基本的に参照されません'''
        super().__init__(
            placeholder='スレッドを選択してください',
            min_values=1,
            max_values=25,
            channel_types=[discord.ChannelType.public_thread, discord.ChannelType.private_thread],
        )
        self.extras = extras
    
    async def callback(self, interaction: discord.Interaction):
        selected_threads = interaction.data['values']
        
        if 'tag' in list(self.extras.keys()):
            await interaction.response.edit_message(
                view=TagView2(
                    extras={
                        'tag': Tag(thread_id=selected_threads[0])
                    }
                )
            )
        return

class MemberSelect(discord.ui.UserSelect):
    def __init__(self, extras: dict | None = None):
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
        selected_users = interaction.data['values']
        thread_id = self.extras['tag'].thread_id
        
        if 'tag' in list(self.extras.keys()):
            await interaction.response.edit_message(
                view=TagView3(
                    extras={
                        'tag': Tag(
                            thread_id=thread_id,
                            users=selected_users
                        )
                    }
                )
            )
        
        return

class DeadlineInputModal(discord.ui.Modal):
    raw_deadline = discord.ui.TextInput(
        placeholder='期限を入力してください (例: )',
        label='期限',
        style=discord.TextStyle.short,
        min_length=1,
        max_length=3900,
    )
    
    def __init__(self, extras: dict | None = None):
        super().__init__(title='期限の入力')
        self.extras = extras
    
    def on_submit(self, interaction: discord.Interaction):
        deadline = self.raw_deadline.value
        
        if 'tag' in list(self.extras.keys()):
            self.extras['tag'].deadline = deadline
            client.tag_manager.add_tag(self.extras['tag'])
        


class ConfimButton(discord.ui.Button):
    def __init__(self, extras: dict | None = None):
        super().__init__(
            label='OK',
            style=discord.ButtonStyle.primary,
        )
        self.extras = extras
    
    async def callback(self, interaction: discord.Interaction):
        pass

class CancelButton(discord.ui.Button):
    def __init__(self, extras: dict | None = None):
        super().__init__(
            label='キャンセル',
            style=discord.ButtonStyle.secondary,
        )
        self.extras = extras
    
    async def callback(self, interaction: discord.Interaction):
        pass


class TagView1(discord.ui.View):
    def __init__(self, extras: dict | None = None):
        super().__init__()
        self.add_item(ThreadsSelect(extras=extras))
        self.add_item(ConfimButton())
        self.add_item(CancelButton())

class TagView2(discord.ui.View):
    def __init__(self, extras: dict | None = None):
        super().__init__()
        self.add_item(MemberSelect(extras=extras))
        self.add_item(ConfimButton())
        self.add_item(CancelButton())

class TagView3(discord.ui.View):
    def __init__(self, extras: dict | None = None):
        super().__init__()
        self.add_item(DeadlineInputModal(extras=extras))
        self.add_item(ConfimButton())
        self.add_item(CancelButton())