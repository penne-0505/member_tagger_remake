import datetime
import discord

from db_manager import Tag


class EmbedManager:
    def __init__(self):
        pass
    
    def format_result(self, result: dict[str, list[dict[str, discord.User | list[dict[str, datetime.datetime]]]]]) -> str:
        '''
        (ユーザーメンション)がタグ付けされているスレッド:
            - (スレッドメンション): (期限(yyyy/mm/dd))
            ...
        
        (スレッドメンション)((期限(yyyy/mm/dd)))にタグ付けされているユーザー:
            - (ユーザーメンション)
            ...
        
        以上のように整形して返す。
        '''
        
        '''
        sample data:
        
        {
            'get_threads_by_user': [
                {
                    'user': <User id=704115683151315055 name='penne0505' global_name='ぺんね' bot=False>,
                    'threads': [
                        {
                            <Thread id=1212549118929543248 name='🛸║あもあす' parent=🍧║どうが owner_id=569651149440024628 locked=False archived=False>: DatetimeWithNanoseconds(2024, 8, 15, 0, 0, tzinfo=datetime.timezone.utc)
                        }
                    ]
                }
            ]
        }
        
        '''
        
        formatted_result = ''
        for mode, data in result.items():
            if mode == 'get_users_by_thread':
                thread = data['thread']
                users = data['users']
                formatted_result += f'{thread.mention}({data["deadline"].strftime("%Y/%m/%d")})にタグ付けされているユーザー:\n'
                for user in users:
                    formatted_result += f'- {user.mention}\n'
            
            elif mode == 'get_threads_by_user':
                messages = []
                for user_dict in data:
                    user_mention = user_dict['user'].mention
                    users_threads = []
                    
                
                

        return formatted_result


    def get_embed(self, data: dict[str, Tag]) -> discord.Embed:
        '''tag must be like ('tag', Tag)'''
        current_mode = list(data.keys())[0]
        if current_mode == 'tag':
            if not data['tag'].thread_id:
                embed = discord.Embed(
                    title='** 1/3 ** スレッドの選択',
                    description='タグ付けするスレッドを選択してください。',
                    color=discord.Color.blue()
                )
                return embed
            
            elif data['tag'].guild_id and data['tag'].thread_id and not data['tag'].users:
                embed = discord.Embed(
                    title='** 2/3 ** メンバーの選択',
                    description='タグ付けするメンバーを選択してください。',
                    color=discord.Color.blue()
                )
                return embed

            elif data['tag'].guild_id and data['tag'].thread_id and data['tag'].users and data['tag'].deadline:
                embed = discord.Embed(
                    title='3/3 タグ付け完了',
                    description='タグ付けが完了しました。',
                    color=discord.Color.green()
                )
                return embed
        
        elif current_mode == 'untag':
            if not data['untag'].thread_id:
                embed = discord.Embed(
                    title='** 1/2 ** スレッドの選択',
                    description='タグを解除するスレッドを選択してください。',
                    color=discord.Color.blue()
                )
                return embed
            
            elif data['untag'].guild_id and data['untag'].thread_id and not data['untag'].users:
                tagged_user_ids = data['untag_tagged_user_ids']
                tagged_users = [data['untag'].client.get_user(int(user_id)) for user_id in tagged_user_ids]
                
                if not tagged_users:
                    description = 'タグ付けされているメンバーは存在しませんでした。'
                else:
                    description = 'タグを解除するメンバーを選択してください。\nタグ付けされているメンバー:\n' + '  \n '.join([user.mention for user in tagged_users])
                
                embed = discord.Embed(
                    title='** 2/2 ** メンバーの選択',
                    description=description,
                    color=discord.Color.blue()
                )
                return embed
            
            elif data['untag'].guild_id and data['untag'].thread_id and data['untag'].users:
                embed = discord.Embed(
                    title='タグ解除完了',
                    description='タグ解除が完了しました。',
                    color=discord.Color.green()
                )
                return embed
        
        elif current_mode == 'get_threads_by_user':
            if not data['get_threads_by_user'].users:
                embed = discord.Embed(
                    title='ユーザーの選択',
                    description='スレッドを取得するユーザーを選択してください。',
                    color=discord.Color.blue()
                )
                return embed
            
            elif data['get_threads_by_user'].users:
                result = self.format_result(data['result'])
                embed = discord.Embed(
                    title='取得結果: ',
                    description=result,
                    color=discord.Color.green()
                )
                return embed
        
        elif current_mode == 'get_users_by_thread':
            if not data['get_users_by_thread'].thread_id:
                embed = discord.Embed(
                    title='スレッドの選択',
                    description='ユーザーを取得するスレッドを選択してください。',
                    color=discord.Color.blue()
                )
                return embed
            
            elif data['get_users_by_thread'].thread_id:
                result = self.format_result(data['result'])
                embed = discord.Embed(
                    title='取得結果: ',
                    description=result,
                    color=discord.Color.green()
                )
                return embed
        
        elif current_mode == 'get_all':
            result = self.format_result(data['result'])
            embed = discord.Embed(
                title='取得結果: ',
                description=result,
                color=discord.Color.green()
            )
            return embed

        elif current_mode == 'toggle_notification':
            past_notification = data['current_notification']
            if past_notification:
                description = '🔕通知をオフにしました。'
            else:
                description = '🔔通知をオンにしました。'
            embed = discord.Embed(
                title='通知設定を変更しました',
                description=description,
                color=discord.Color.green()
            )
            return embed
        
        elif current_mode == 'cancel':
            embed = discord.Embed(
                title='キャンセル',
                description='キャンセルしました。',
                color=discord.Color.yellow()
            )
            return embed