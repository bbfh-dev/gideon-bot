import json
import os
import pathlib
import time
import uuid

import discord

__db__ = os.path.join(
    os.path.dirname(os.path.realpath(__file__)),
    "..",
    "..",
    "database.json",
)


class Database:
    class PermLevel:
        def __init__(self, data: dict):
            self.root: list[int] = data.get("root")
            self.manager: list[int] = data.get("manager")

        def __export__(self):
            return {
                "root": self.root,
                "manager": self.manager,
            }

    class Clans:
        class Clan:
            class Roles:
                class Role:
                    def __init__(self, data: dict):
                        self.id: int = data.get("id")
                        self.name: str = data.get("name")
                        self.icon: str = data.get("icon")
                        self.discord: int = data.get("discord")

                    def __export__(self):
                        return {
                            "id": self.id,
                            "name": self.name,
                            "icon": self.icon,
                            "discord": self.discord,
                        }

                def __init__(self, data: list[dict]):
                    self._list = [self.Role(entry) for entry in data]

                def __export__(self):
                    return [item.__export__() for item in self._list]

                def get(self, index: int) -> Role | None:
                    for item in self._list:
                        if item.id == index:
                            return item
                    return None

                def get_name(self, index: int):
                    item = self.get(index)
                    return "<?>" if not item else item.name

                def __list__(self):
                    return self._list

            def __init__(self, data: dict):
                self.id: int = data.get("id")
                self.name: str = data.get("name")
                self.guild: int = data.get("guild")
                self.roles = self.Roles(data.get("roles"))

            def __export__(self):
                return {
                    "id": self.id,
                    "name": self.name,
                    "guild": self.guild,
                    "roles": self.roles.__export__(),
                }

        def __init__(self, data: list[dict]):
            self._list = [self.Clan(entry) for entry in data]

        def __export__(self):
            return [item.__export__() for item in self._list]

        def __list__(self):
            return self._list

        def get(self, index: int) -> Clan | None:
            for item in self._list:
                if item.id == index:
                    return item
            return None

        def find(self, name: str) -> Clan | None:
            for item in self._list:
                if item.name.lower() == name:
                    return item
            return None

    class Players:
        class Player:
            class Clans:
                class Clan:
                    def __init__(self, data: dict):
                        self.clan: int = data.get("clan")
                        self.primary: bool = data.get("primary")
                        self.role: int = data.get("role")

                    def __export__(self):
                        return {
                            "clan": self.clan,
                            "primary": self.primary,
                            "role": self.role,
                        }

                    def resolve_clan(self):
                        return BOT.db.clans.get(self.clan)

                    def resolve_role(self):
                        return BOT.db.clans.get(self.clan).roles.get(self.role)

                def __init__(self, data: list[dict]):
                    self.list = [self.Clan(entry) for entry in data]

                def __list__(self):
                    return self.list

                def __export__(self):
                    return [item.__export__() for item in self.list]

            def __init__(self, data: dict):
                self.parents: list[str] | None = data.get("parents")
                self.uuid: str = data.get("uuid")
                self.name: str = data.get("name")
                self.hidden: bool = data.get("hidden")
                self.last_updated: float = data.get("last_updated") or time.time()
                self.discord: int = data.get("discord")
                self.slug: str = data.get("slug")
                self.clans = self.Clans(data.get("clans"))

            def __export__(self):
                return {
                    "parents": self.parents,
                    "uuid": self.uuid,
                    "name": self.name,
                    "hidden": self.hidden,
                    "last_updated": self.last_updated,
                    "discord": self.discord,
                    "slug": self.slug,
                    "clans": self.clans.__export__(),
                }

            def auto_name(self):
                if self.parents:
                    return f"{self.name} (Alt)"
                return self.name

            def auto_discord(self):
                if self.parents:
                    return [
                        BOT.db.players.find_by_uuid(parent).discord
                        for parent in self.parents
                    ]
                return self.discord

            def auto_slug(self):
                if self.parents:
                    return [
                        BOT.db.players.find_by_uuid(parent).slug
                        for parent in self.parents
                    ]
                return self.slug

            def resolve_parent(self):
                if not self.parents:
                    return None
                return [BOT.db.players.find_by_uuid(parent) for parent in self.parents]

            def auto_clans(self):
                if self.parents:
                    merged = []
                    for parent in self.parents:
                        merged = [
                            *merged,
                            *BOT.db.players.find_by_uuid(parent).clans.__export__(),
                        ]
                    return self.Clans(merged)
                return self.clans

            def print_clans(self):
                return [
                    "- " + "??"
                    if not clan.resolve_role()
                    else clan.resolve_role().icon
                    + " **"
                    + ("__" if clan.primary else "")
                    + clan.resolve_clan().name
                    + ("__" if clan.primary else "")
                    + f"** (`{'???' if not clan.resolve_role() else clan.resolve_role().name}`)"
                    for clan in self.auto_clans().__list__()
                ]

        def __init__(self, data: list[dict]):
            self._list = [self.Player(entry) for entry in data]

        def __export__(self):
            return [item.__export__() for item in self._list]

        def __list__(self):
            return self._list

        def set(self, index: int, value):
            self._list[index].name = value
            self._list[index].last_updated = time.time()
            BOT.db.save()

        def update(self, uuid: str, discord_id: int, clan_id: int, role_id: int):
            for index, player in enumerate(self._list):
                if player.uuid == uuid:
                    self._list[index].discord = discord_id
                    self._list[index].clans.list.append(self.Player.Clans.Clan({
                        "clan"   : clan_id,
                        "primary": False,
                        "role"   : role_id,
                    }))
            BOT.db.save()

        def unify(self):
            uuids = []
            for index, player in enumerate(self._list):
                if player.uuid in uuids:
                    self._list.pop(index)
                uuids.append(player.uuid)
            BOT.db.save()

        def modify_by_uuid(self, uuid: str, clan: int, role: int):
            for index, entry in enumerate(self._list):
                if entry.uuid == uuid:
                    for j, c in enumerate(entry.clans.__list__()):
                        if c.resolve_clan().id == clan:
                            self._list[index].clans.list[j].role = role
                            BOT.db.save()
                            return

        def find_by_ign(self, ign: str) -> Player | None:
            ign = ign.lower()
            for entry in self._list:
                if entry.name.lower() == ign:
                    return entry
            return None

        def delete(self, uuid: str):
            for index, entry in enumerate(self._list):
                if entry.uuid == uuid:
                    self._list.pop(index)
            BOT.db.save()

        def find_by_uuid(self, uuid: str) -> Player | None:
            for entry in self._list:
                if entry.uuid == uuid:
                    return entry
            return None

        def find_by_discord(self, index: int) -> Player | None:
            for entry in self._list:
                if entry.discord == index:
                    return entry
            return None

        def get_alts_by_uuid(self, uuid: str) -> tuple[list[Player], list[Player]]:
            """
            :return: (PUBLIC[], PRIVATE[])
            """
            result = []
            for entry in self._list:
                if entry.parents and uuid in entry.parents:
                    result.append(entry)
            return (
                [i for i in result if not i.hidden],
                [i for i in result if i.hidden],
            )

        def add(
            self,
            parents: list[str] | None,
            uuid: str,
            name: str,
            hidden: bool,
            _discord,
            _slug,
            clan: dict,
        ):
            self._list.append(
                self.Player(
                    {
                        "parents": parents,
                        "uuid": uuid,
                        "name": name,
                        "hidden": hidden,
                        "last_updated": time.time(),
                        "discord": _discord,
                        "slug": _slug,
                        "clans": [clan],
                    }
                )
            )
            BOT.db.save()

        def sort(self):
            def sort_lambda(player):
                return player.last_updated

            self._list.sort(key=sort_lambda)
            BOT.db.save()

    def __init__(self, data: dict):
        self.token: str = data.get("token")
        self.home: int = data.get("home")
        self.perm_level = self.PermLevel(data.get("perm_level"))
        self.clans = self.Clans(data.get("clans"))
        self.clan_relations = data.get("clan_relations")
        self.players = self.Players(data.get("players"))

    def __export__(self):
        return {
            "token": self.token,
            "home": self.home,
            "perm_level": self.perm_level.__export__(),
            "clans": self.clans.__export__(),
            "clan_relations": self.clan_relations,
            "players": self.players.__export__(),
        }

    def save(self):
        with open(__db__, "w") as fp:
            json.dump(self.__export__(), fp, indent=4)

    def find_clan(self, index: int) -> Clans.Clan | None:
        for clan in self.clans.__list__():
            if clan.guild == index:
                return clan
        return None

    def get_role(
        self, roles: Clans.Clan.Roles, member: discord.Member
    ) -> Clans.Clan.Roles.Role | None:
        for role in roles.__list__():
            if role.discord in [r.id for r in member.roles]:
                return role
        return None


class Bot(discord.Bot):
    def __init__(self, *args, **options):
        self.db: None | Database = None
        self.ready_status = False
        self.prefix = "gd:"
        self.path = pathlib.Path(__file__).parent.parent.parent.absolute()
        self.memory: list[discord.TextChannel] = []

        super().__init__(*args, **options)

    def __bool__(self):
        return self.ready_status and self.db is not None

    async def not_ready(self, message: discord.Message):
        await message.add_reaction("🚫")
        return self


BOT = Bot(intents=discord.Intents.all())
