# db_manager.py:

import datetime
import os

import discord
import firebase_admin
import requests
from firebase_admin import credentials, firestore

import utils
from utils import Tag, Task


class DBManager(metaclass=utils.Singleton):
    def __init__(self):
        url = os.getenv("MEMBER_TAGGER_FIREBASE_CREDENTIALS")
        self.cred = credentials.Certificate(requests.get(url).json())
        firebase_admin.initialize_app(self.cred)
        self.db = firestore.client()

    def set(self, collection: str, document: str | None, data: dict) -> bool:
        try:
            if document:
                self.db.collection(collection).document(document).set(data)
            else:
                self.db.collection(collection).add(data)
            return True
        except Exception as e:
            print(e)
            return False

    def get(self, collection: str, document: str | None = None) -> dict:
        try:
            doc_ref = (
                self.db.collection(collection).document(document)
                if document
                else self.db.collection(collection)
            )
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

    def add_document(
        self,
        collection: str,
        document_data: dict,
        document_id: str,
        timeout_sec: int | float = None,
    ) -> bool:
        try:
            if not timeout_sec:
                self.db.collection(collection).add(document_data, document_id)
            else:
                self.db.collection(collection).add(
                    document_data, document_id, timeout_sec
                )

            return True
        except Exception as e:
            print(e)
            return False

    def delete_collection(self, collection: str, batch_size: int = 10):
        # コレクション内のドキュメントを削除
        docs = self.db.collection(collection).limit(batch_size).stream()
        deleted = 0
        for doc in docs:
            doc.reference.delete()
            deleted += 1
        if deleted >= batch_size:
            return self.delete_collection(collection, batch_size)
        return


# TODO: TagManager全体のメソッドにおいて、一度のアクセスで追加・削除・取得を行うように変更
class TagManager:
    def __init__(self):
        self.db_manager = DBManager()

    def add_tag(self, tag: Tag):
        for user in tag.users:
            user_id = user.id
            fetched_user = self.db_manager.get("users", str(user_id))
            # 存在しないキーの配下に新しいキーを追加するとエラーが発生するため、キーが存在しない場合は追加する
            if str(tag.guild_id) not in fetched_user["tags"]:
                fetched_user["tags"][str(tag.guild_id)] = {}
            if str(tag.thread_id) not in fetched_user["tags"][str(tag.guild_id)]:
                fetched_user["tags"][str(tag.guild_id)][str(tag.thread_id)] = (
                    tag.deadline
                )
            else:
                fetched_user["tags"][str(tag.guild_id)][str(tag.thread_id)] = (
                    tag.deadline
                )
            self.db_manager.update("users", str(user_id), fetched_user)

    def remove_tag(self, tag: Tag):
        for user in tag.users:
            user_id = user.id
            fetched_user = self.db_manager.get("users", str(user_id))
            fetched_user["tags"][str(tag.guild_id)].pop(str(tag.thread_id))
            # もし、guild_id配下にthread_idが存在しなくなった場合は、guild_idを削除
            if not fetched_user["tags"][str(tag.guild_id)]:
                fetched_user["tags"].pop(str(tag.guild_id))

            self.db_manager.update("users", str(user_id), fetched_user)

    def get_tags(self, user: discord.User):
        fetched_user = self.db_manager.get("users", str(user.id))
        return fetched_user["tags"]

    def update_tag(self, tag: Tag):
        for user in tag.users:
            user_id = user.id
            fetched_user = self.db_manager.get("users", str(user_id))
            fetched_user["tags"][str(tag.guild_id)][str(tag.thread_id)] = tag.deadline
            self.db_manager.update("users", str(user_id), fetched_user)

    def get_users_by_thread(self, tag: Tag):
        guild_id = tag.guild_id
        thread_id = tag.thread_id
        user_ids = []
        fetched_user = self.db_manager.get("users")
        # ユーザーごとに、ギルドIDとスレッドIDが一致するかを確認し、一致する場合はユーザーIDをリストに追加

        for user in fetched_user:
            if (
                str(guild_id) in user["tags"]
                and str(thread_id) in user["tags"][str(guild_id)]
            ):
                user_ids.append(tag.client.get_user(user["user_id"]))

        return user_ids

    def get_threads_by_user(
        self, users: list[discord.User]
    ) -> dict[str, list[tuple[str, datetime.datetime]]]:
        for user in users:
            user_id = user.id
            fetched_user = self.db_manager.get("users", str(user_id))
            threads = {}
            for guild_id in fetched_user["tags"].keys():
                guild_threads = []
                for thread_id in fetched_user["tags"][guild_id].items():
                    guild_threads.append(thread_id)
                threads[guild_id] = guild_threads
        return threads

    def add_user(self, user: discord.User):
        user_data = {
            "user_id": user.id,
            "name": user.name,
            "notification": True,
            "tasks": {},
            "tags": {},
        }
        self.db_manager.set("users", str(user.id), user_data)

    def remove_user(self, user: discord.User):
        self.db_manager.delete("users", str(user.id))

    def get_user(self, user: discord.User):
        return self.db_manager.get("users", str(user.id))

    def get_all_users(self):
        return self.db_manager.get("users")

    def update_user(self, user: discord.User, data: dict):
        right_data_schema = {
            "user_id": int,
            "name": str,
            "notification": bool,
            "tasks": dict[str, str | dict],
            "tags": dict[str, dict[str, datetime.datetime]],
        }
        for key in data.keys():
            if not list(data.keys()) == list(right_data_schema.keys()):
                raise ValueError(f"Invalid key name. (key: {key})")
            if not isinstance(data[key], right_data_schema[key]):
                raise ValueError(f"Invalid data type. (key: {key})")

        self.db_manager.update("users", str(user.id), data)

    def add_task(self, task: Task):
        # 重複しないtask_idを生成
        task_id = utils.generate_id()
        user = task.user
        user_data = self.db_manager.get("users", str(user.id))
        user_data["tasks"][task_id] = task.content
        # 生成したtask_idをused_idsに追加
        if "used_ids" not in user_data["tasks"]:
            user_data["tasks"]["used_ids"] = [task_id]
        else:
            user_data["tasks"]["used_ids"].append(task_id)
        self.db_manager.update("users", str(user.id), user_data)

    def delete_task(self, task: Task):
        user = task.user
        task_id = task.task_id
        fetched_user = self.db_manager.get("users", str(user.id))
        fetched_user["tasks"].pop(task_id)
        fetched_user["tasks"]["used_ids"].remove(task_id)
        self.db_manager.update("users", str(user.id), fetched_user)

    def get_tasks(self, task: Task):
        user = task.user
        fetched_user = self.db_manager.get("users", str(user.id))
        return fetched_user["tasks"]

    def update_task(self, task: Task):
        user = task.user
        task_id = task.task_id
        content = task.content
        fetched_user = self.db_manager.get("users", str(user.id))
        fetched_user["tasks"][task_id] = content
        self.db_manager.update("users", str(user.id), fetched_user)

    def toggle_notification(self, user: discord.User) -> bool:
        fetched_user = self.db_manager.get("users", str(user.id))
        fetched_user["notification"] = not fetched_user["notification"]
        self.db_manager.update("users", str(user.id), fetched_user)
        return fetched_user["notification"]

    def add_notify_channel(
        self, channel=dict[discord.Guild, discord.TextChannel | discord.Thread | None]
    ):
        use_set = False
        fetched_user = self.db_manager.get("notify", "notify_channels")

        if not fetched_user:
            use_set = True
            fetched_user = {}

        for guild, ch in channel.items():
            fetched_user[str(guild.id)] = ch.id if ch else None

        # 存在しないキーのupdateは使用できないため、そのような場合はsetを使用
        if use_set:
            self.db_manager.set("notify", "notify_channels", fetched_user)
        else:
            self.db_manager.update("notify", "notify_channels", fetched_user)

    def get_notify_channel(
        self, guild_id: str
    ) -> dict[
        str, str | None
    ]:  # dict[discord.Guild.id, discord.TextChannel.id | discord.Thread.id | None]
        return self.db_manager.get("notify", "notify_channels")[guild_id]

    def delete_notify_channel(self, guild: discord.Guild):
        fetched_user = self.db_manager.get("notify", "notify_channels")
        fetched_user.pop(str(guild.id))
        self.db_manager.update("notify", "notify_channels", fetched_user)


if __name__ == "__main__":
    print("This is a library file and cannot be executed directly.")
