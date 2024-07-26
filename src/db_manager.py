import asyncio
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
    
    def get(self, collection: str, document: str | None) -> dict:
        try:
            doc_ref = self.db.collection(collection).document(document) if document else self.db.collection(collection)
            doc = doc_ref.get()
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


class TagManager:
    def __init__(self):
        self.db_manager = DBManager()
    
    def set_user(self, user_id: int, user_name: str):
        # ユーザーが登録されていなかった場合、ユーザーを登録
        if not self.db_manager.get('users', str(user_id)):
            self.db_manager.set('users', str(user_id), {'name': user_name, 'notification': True, 'threads': {}, 'tasks': {}})
        return
    
    def set_users(self, users: list[discord.User]):
        for user in users:
            self.set_user(user.id, user.name) if not self.db_manager.get('users', user.id) else None
        return
    
    def set_thread(self, user_id: int, guild_id: int, thread_id: int, deadline: datetime.datetime):
        # すでにスレッドが登録されていた場合は何もしない
        if thread_id in (self.db_manager.get('users', user_id))['threads']:
            return
        else:
            # スレッドが登録されていなかった場合、スレッドを登録
            self.db_manager.update('users', user_id, {f'threads.{guild_id}.{thread_id}': deadline})
    
    def set_threads(self, user_id: int, threads: list[dict]):
        '''
        threads dict must be like:
        [
            {
                guild_id: {
                    thread_id: deadline
                }
            }
            ...
        ]
        '''
        for thread in threads:
            for guild_id in thread:
                for thread_id, deadline in thread[guild_id].items():
                    self.set_thread(user_id, guild_id, thread_id, deadline)
    
    def set_tasks(self, user_id: int, tasks: dict):
        # タスクを更新
        self.db_manager.update('users', user_id, {'tasks': tasks})
        return
    
    def set_deadline(self, user_id: int, guild_id: int, thread_id: int, deadline: datetime.datetime):
        # スレッドの締切日時を更新
        self.db_manager.update('users', user_id, {f'threads.{guild_id}.{thread_id}': deadline})
        return
    
    # このguildsは、このbotが参加しているguildを登録しておくもので、この中にthreadの情報は入れない
    def set_guild(self, guild_id: int):
        # ギルドが登録されていなかった場合、ギルドを登録
        if not self.db_manager.get('guilds', guild_id):
            self.db_manager.set('guilds', guild_id, {})
        return
    
    def get_tasks(self, user_id: int) -> dict:
        # タスクを取得
        return self.db_manager.get('users', user_id)['tasks']

    def get_notification_status(self, user_id: int) -> bool:
        # ユーザーの通知設定を取得
        return (self.db_manager.get('users', user_id))['notification']
    
    def get_threads(self, user_id: int) -> dict:
        # ユーザーのスレッド情報を取得
        return self.db_manager.get('users', user_id)['threads']

    def get_all_guilds(self) -> list[int]:
        # ギルドIDを取得
        return [int(guild) for guild in self.db_manager.get('guilds', None)]
    
    def get_users_by_thread(self, guild_id: int, thread_id: int) -> list[dict]:
        # スレッドに登録されているユーザーを取得
        users = self.db_manager.get('users', None)
        # スレッドに登録されているユーザーの情報を返す
        return [user for user in users if thread_id in users[user]['threads'][guild_id]]
    
    def get_deadline(self, user_id: int, guild_id: int, thread_id: int) -> datetime.datetime:
        # スレッドの締切日時を取得
        return (self.db_manager.get('users', user_id))['threads'][guild_id][thread_id]
    
    def toggle_notification(self, user_id: int):
        # 現在の通知設定を取得
        notification = self.get_notification_status(user_id)
        # 通知設定を反転
        self.db_manager.update('users', user_id, {'notification': not notification})
        return
    
    def update_user_info(self, user_id: int, data: dict):
        # ユーザー情報を更新
        self.db_manager.update('users', user_id, data)
        return
    
    def delete_thread(self, user_id: int, guild_id: int, thread_id: int):
        # スレッドが登録されていなかった場合は何もしない
        if thread_id not in (self.db_manager.get('users', user_id))['threads']:
            return
        else:
            # 操作するスレッドの情報を取得
            threads = (self.db_manager.get('users', user_id))['threads'][guild_id]
            # スレッドを削除
            threads.pop(thread_id)
            # スレッドを更新
            self.db_manager.update('users', user_id, {f'threads.{guild_id}': threads})
            return
    
    def delete_user(self, user_id: int):
        # ユーザーを削除
        self.db_manager.delete('users', user_id)
        return

    def delete_tasks(self, user_id: int):
        # タスクを削除
        self.db_manager.update('users', user_id, {'tasks': {}})
        return


if __name__ == '__main__':
    print('This is a library file and cannot be executed directly.')