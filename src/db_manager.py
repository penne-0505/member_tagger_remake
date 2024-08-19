from dataclasses import dataclass
import datetime
import os

import discord
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore

import utils as utils


class DBManager(metaclass=utils.Singleton):
    def __init__(self):
        self.cred = credentials.Certificate(os.getenv('MEMBER_TAGGER_FIREBASE_CREDENTIALS'))
        firebase_admin.initialize_app(self.cred)
        self.db = firestore.client()
    
    def set(self, collection: str, document: str | None, data: dict) -> bool:
        try:
            self.db.collection(collection).document(document).set(data) if document else self.db.collection(collection).add(data)
            return True
        except Exception as e:
            print(e)
            return False
    
    def get(self, collection: str, document: str | None=None) -> dict:
        try:
            doc_ref = self.db.collection(collection).document(document) if document else self.db.collection(collection)
            doc = doc_ref.get()
            if isinstance(doc, list):
                return [d.to_dict() for d in doc]
            else:
                return doc.to_dict()
        except Exception as e:
            print(e)
            return {}
    
    def update(self, collection: str, document: str, data: dict) -> bool:
        try:
            self.db.collection(collection).document(document).update(data)
            return True
        except Exception as e:
            print(e)
            return False
    
    def delete(self, collection: str, document: str) -> bool:
        try:
            self.db.collection(collection).document(document).delete()
            return True
        except Exception as e:
            print(e)
            return False
    
    def add_document(self, collection: str, document_data: dict, document_id: str, timeout_sec: int | float=None) -> bool:
        try:
            # コレクションにドキュメントを追加
            self.db.collection(collection).add(document_data, document_id) if not timeout_sec else self.db.collection(collection).add(document_data, document_id, timeout_sec)
            return True
        except Exception as e:
            print(e)
            return False
    
    def delete_collection(self, collection: str, batch_size: int=10):
        # コレクション内のドキュメントを削除
        docs = self.db.collection(collection).limit(batch_size).stream()
        deleted = 0
        for doc in docs:
            doc.reference.delete()
            deleted += 1
        if deleted >= batch_size:
            return self.delete_collection(collection, batch_size)
        return


'''
### db architecture
@startjson
db = {
    'users': {
        (user_id: int): {
            'name': (str),
            'notification': (bool),
            'tasks': {
                'used_ids': [(task_id: str)],
                (task_id: str): {
                    'content': (str),
                }
                ...
            },
            'tags': {
                (guild_id: int): {
                    (thread_id: int): (deadline: datetime.datetime), # deadlineの実際の型はtimestamp
                }
            }
        }
        ...
    }
}
@endjson
### Tag class

Tag: 
    guild_id: int
    thread_id: int
    users: list[discord.User]
    deadline: datetime.datetime
'''

@dataclass
class Tag:
    client: discord.Client = None
    guild_id: int = None
    thread_id: int = None
    users: list[discord.User] = None
    deadline: datetime.datetime = None

class TagManager:
    def __init__(self):
        self.db_manager = DBManager()
    
    def add_tag(self, tag: Tag):
        for user in tag.users:
            user_id = user.id
            user_data = self.db_manager.get('users', str(user_id))
            # 存在しないキーの配下に新しいキーを追加するとエラーが発生するため、キーが存在しない場合は追加する
            if str(tag.guild_id) not in user_data['tags']:
                user_data['tags'][str(tag.guild_id)] = {}
            if str(tag.thread_id) not in user_data['tags'][str(tag.guild_id)]:
                user_data['tags'][str(tag.guild_id)][str(tag.thread_id)] = tag.deadline
            else:
                user_data['tags'][str(tag.guild_id)][str(tag.thread_id)] = tag.deadline
            self.db_manager.update('users', str(user_id), user_data)
    
    def remove_tag(self, tag: Tag):
        for user in tag.users:
            user_id = user.id
            user_data = self.db_manager.get('users', str(user_id))
            user_data['tags'][str(tag.guild_id)].pop(str(tag.thread_id))
            # もし、guild_id配下にthread_idが存在しなくなった場合は、guild_idを削除
            if not user_data['tags'][str(tag.guild_id)]:
                user_data['tags'].pop(str(tag.guild_id))
            
            self.db_manager.update('users', str(user_id), user_data)
    
    def get_tags(self, user: discord.User):
        user_data = self.db_manager.get('users', str(user.id))
        return user_data['tags']
    
    def update_tag(self, tag: Tag):
        for user in tag.users:
            user_id = user.id
            user_data = self.db_manager.get('users', str(user_id))
            user_data['tags'][str(tag.guild_id)][str(tag.thread_id)] = tag.deadline
            self.db_manager.update('users', str(user_id), user_data)
    
    def get_users_by_thread(self, tag: Tag):
        thread_id = tag.thread_id
        user_ids = []
        user_data = self.db_manager.get('users')
        '''
        サンプルデータ
        [{'notification': True, 'user_id': 1021394941743734814, 'tasks': {}, 'tags': {}, 'name': 'mamadaisuki.'}, {'notification': True, 'user_id': 1038733998630899743, 'tasks': {}, 'tags': {}, 'name': 'error.428'}, {'notification': True, 'user_id': 569651149440024628, 'tasks': {}, 'tags': {}, 'name': 'onigiri_oo'}, {'notification': True, 'user_id': 641764833460748295, 'tasks': {}, 'tags': {}, 'name': 'chongyanjing8744'}, {'notification': True, 'user_id': 687202120969355284, 'tasks': {}, 'tags': {}, 'name': 'zapks'}, {'notification': True, 'user_id': 704115683151315055, 'tasks': {}, 'tags': {'1039814831395569676': {'1270798541970739200': DatetimeWithNanoseconds(2020, 1, 1, 0, 0, tzinfo=datetime.timezone.utc)}, '884682745429766164': {'1272926429960732763': DatetimeWithNanoseconds(2024, 8, 13, 0, 0, tzinfo=datetime.timezone.utc), '1212549118929543248': DatetimeWithNanoseconds(2024, 8, 15, 0, 0, tzinfo=datetime.timezone.utc)}}, 'name': 'penne0505'}, {'notification': True, 'user_id': 711421164194365471, 'tasks': {}, 'tags': {}, 'name': 'rarorurerin'}, {'notification': True, 'user_id': 712503770931527778, 'tasks': {}, 'tags': {}, 'name': 'piplup_lv.5'}, {'notification': True, 'user_id': 720241890662023268, 'tasks': {}, 'tags': {}, 'name': 'sasasasawamura'}, {'notification': True, 'user_id': 730778811263746062, 'tasks': {}, 'tags': {}, 'name': 'aoi053112'}, {'notification': True, 'user_id': 756101891548512287, 'tasks': {}, 'tags': {}, 'name': 'fookurou'}, {'notification': True, 'user_id': 824616112909058058, 'tasks': {}, 'tags': {}, 'name': 'yamamoto_katsuyoshi'}, {'notification': True, 'user_id': 843146360244011008, 'tasks': {}, 'tags': {}, 'name': 'aki5672'}, {'notification': True, 'user_id': 867192594962055178, 'tasks': {}, 'tags': {}, 'name': 'tarabaebi'}, {'notification': True, 'user_id': 886465290785918996, 'tasks': {}, 'tags': {}, 'name': 'fukimayu'}, {'notification': True, 'user_id': 907286924354551829, 'tasks': {}, 'tags': {}, 'name': 'testbot.'}, {'notification': True, 'user_id': 912553432093712434, 'tasks': {}, 'tags': {}, 'name': 'tarabagai_ebi'}, {'notification': True, 'user_id': 938704672905105439, 'tasks': {}, 'tags': {}, 'name': 'obzerver381ribenrendesu9041'}, {'notification': True, 'user_id': 948937635806707762, 'tasks': {}, 'tags': {}, 'name': 'xizhuzhenshu7946'}, {'notification': True, 'user_id': 957815990425624596, 'tasks': {}, 'tags': {}, 'name': 'yutsukurishikuangebichiyanneru'}, {'notification': True, 'user_id': 958492903217451069, 'tasks': {}, 'tags': {}, 'name': 'f.ka0311'}, {'notification': True, 'user_id': 966630541950586900, 'tasks': {}, 'tags': {}, 'name': 'mont7465'}, {'notification': True, 'user_id': 972763598625574995, 'tasks': {}, 'tags': {}, 'name': 'kyohakarakuti'}]
        '''
        # ユーザーごとに、ギルドIDとスレッドIDが一致するかを確認し、一致する場合はユーザーIDをリストに追加
        for user in user_data:
            if str(tag.guild_id) in user['tags'] and str(thread_id) in user['tags'][str(tag.guild_id)]:
                user_ids.append(tag.client.get_user(user['user_id']))

        return user_ids

    def get_threads_by_user(self, users: list[discord.User]) -> dict[str, list[tuple[str, datetime.datetime]]]:
        '''
        {
            (guild_id: str): [
                (thread_id: str, deadline: datetime.datetime),
                ...
            ]
        }
        '''
        for user in users:
            user_id = user.id
            user_data = self.db_manager.get('users', str(user_id))
            threads = {}
            for guild_id in user_data['tags'].keys():
                guild_threads = []
                for thread_id in user_data['tags'][guild_id].items():
                    guild_threads.append(thread_id)
                threads[guild_id] = guild_threads
        return threads

    def add_user(self, user: discord.User):
        user_data = {
            'user_id': user.id,
            'name': user.name,
            'notification': True,
            'tasks': {},
            'tags': {}
        }
        self.db_manager.set('users', str(user.id), user_data)
    
    def remove_user(self, user: discord.User):
        self.db_manager.delete('users', str(user.id))
    
    def get_user(self, user: discord.User):
        return self.db_manager.get('users', str(user.id))

    def get_all_users(self):
        return self.db_manager.get('users')

    def update_user(self, user: discord.User, data: dict):
        right_data_schema = {
            'user_id': int,
            'name': str,
            'notification': bool,
            'tasks': dict[str, str | dict],
            'tags': dict[str, dict[str, datetime.datetime]]
        }
        for key in data.keys():
            if not list(data.keys()) == list(right_data_schema.keys()):
                raise ValueError(f'Invalid key name. (key: {key})')
            if not isinstance(data[key], right_data_schema[key]):
                raise ValueError(f'Invalid data type. (key: {key})')
        
        self.db_manager.update('users', str(user.id), data)
    
    def add_task(self, user: discord.User, content: str):
        # 重複しないtask_idを生成
        used_ids = self.db_manager.get('users', str(user.id))['tasks']['used_ids']
        while task_id in used_ids:
            task_id = utils.generate_id()
        used_ids.append(task_id)
        self.db_manager.update('users', str(user.id), {'tasks': {'used_ids': used_ids}})
        # taskを追加
        user_data = self.db_manager.get('users', str(user.id))
        user_data['tasks'][task_id] = content
        self.db_manager.update('users', str(user.id), user_data)
    
    def remove_task(self, user: discord.User, task_id: str):
        user_data = self.db_manager.get('users', str(user.id))
        user_data['tasks'].pop(task_id)
        self.db_manager.update('users', str(user.id), user_data)
    
    def get_tasks(self, user: discord.User):
        return self.db_manager.get('users', str(user.id))['tasks']

    def update_task(self, user: discord.User, task_id: str, content: str):
        user_data = self.db_manager.get('users', str(user.id))
        user_data['tasks'][task_id] = content
        self.db_manager.update('users', str(user.id), user_data)
    
    def toggle_notification(self, user: discord.User) -> bool:
        user_data = self.db_manager.get('users', str(user.id))
        user_data['notification'] = not user_data['notification']
        self.db_manager.update('users', str(user.id), user_data)
        return user_data['notification']


if __name__ == '__main__':
    print('This is a library file and cannot be executed directly.')