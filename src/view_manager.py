import discord


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
    
    async def callback(self, interaction: discord.Interaction):
        # メンバーを選択するviewに遷移
        selected_threads = interaction.data['values']
        print(selected_threads)
        pass

class MemberSelect(discord.ui.UserSelect):
    def __init__(self, extras: dict | None = None):
        '''
        extrasは、tag,untagモードの場合は
        {
            'tag': (thread_id: int),
        }
        のようになっている必要があります
        
        '''
        super().__init__(
            placeholder='ユーザーを選択してください',
            min_values=1,
            max_values=25,
        )
    
    async def callback(self, interaction: discord.Interaction):
        # deadlineを入力するviewに遷移
        selected_users = interaction.data['values']
        print(selected_users)
        pass

class DeadlineInputModal(discord.ui.Modal):
    raw_deadline = discord.ui.TextInput(
        placeholder='期限を入力してください',
        label='期限',
        style=discord.TextStyle.short,
        min_length=1,
        max_length=3900,
    )
    
    def __init__(self, extras: dict | None = None):
        super().__init__(title='期限の入力')
        self.extras = extras
    
    def on_submit(self, interaction: discord.Interaction):
        # ここでmain.pyのcallbackを呼び出す
        deadline = self.raw_deadline.value
        print(deadline)
        pass

class ConfimButton(discord.ui.Button):
    def __init__(self, extras: dict | None = None):
        super().__init__(
            label='OK',
            style=discord.ButtonStyle.primary,
        )
    
    async def callback(self, interaction: discord.Interaction):
        pass

class CancelButton(discord.ui.Button):
    def __init__(self, extras: dict | None = None):
        super().__init__(
            label='キャンセル',
            style=discord.ButtonStyle.secondary,
        )
    
    async def callback(self, interaction: discord.Interaction):
        pass


class TagView1(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.add_item(ThreadsSelect())
        self.add_item(ConfimButton())
        self.add_item(CancelButton())

class TagView2(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.add_item(MemberSelect())
        self.add_item(ConfimButton())
        self.add_item(CancelButton())
