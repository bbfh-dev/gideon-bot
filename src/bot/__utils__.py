import re
import time
from dataclasses import dataclass

import discord


class ClanType:
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


class PlayerType:
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
                pass

            def resolve_role(self):
                pass

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
            return []
        return self.discord

    def auto_slug(self):
        if self.parents:
            return []
        return self.slug

    def resolve_parent(self):
        if not self.parents:
            return None
        return []

    def auto_clans(self):
        if self.parents:
            merged = []
            for parent in self.parents:
                merged = []
            return self.Clans(merged)
        return self.clans


def get_icon(member: discord.Member):
    if not member:
        return ""
    return (
        member.default_avatar.url
        if not member.display_avatar
        else member.display_avatar.url
    )


def get_name(member: discord.Member):
    __split = str(member).split("#")
    return __split[0] if len(__split[1]) <= 1 else str(member)


def strip_name(member: discord.Member):
    return (
        re.sub(r"\[(.*?)\]", "", re.sub(r"\([^()]*\)", "", member.display_name))
        .split("|")[0]
        .split(" ")[0]
        .replace(".", "")
    )


async def print_roster(
    last_updated: float,
    relations: list[list[int]],
    index: int,
    clan: ClanType,
    channel: discord.TextChannel,
    clans,
    db_players: list[PlayerType],
    BOT
):
    @dataclass
    class RosterPlayer:
        name: str
        role: ClanType.Roles.Role

    enemies = [clans.get(i).name for i, r in enumerate(relations[index]) if r == 3]
    allies = [clans.get(i).name for i, r in enumerate(relations[index]) if r == 2]
    neutrals = [clans.get(i).name for i, r in enumerate(relations[index]) if r == 1]

    players: list[RosterPlayer] = []
    messages = [
        f"> ## - Roster of {clan.name}\n"
        f"> **Last updated** <t:{round(time.time())}:R>\n"
        f"> **Usernames are up-to-date as of** <t:{round(last_updated)}:R>\n"
        f"> :small_orange_diamond: **Enemy clans**: `{', '.join(enemies) or '---'}`\n"
        f"> :small_blue_diamond: **Allied clans**: `{', '.join(allies) or '---'}`\n"
        f"> :white_small_square: **Neutral clans**: `{', '.join(neutrals) or '---'}`\n"
        f"> *Rosters aren't 100% accurate. Feel free to message @bbfh to add/remove/edit somebody.*\n"
    ]
    roles = clan.roles.__list__()
    roles.sort(key=lambda r: r.id)
    for role in roles:
        for player in [i for i in db_players if not i.parents and role.id in [j.role for j in i.clans.list if j.clan == clan.id]]:
            name = player.name.replace("_", "\\_")
            if player.discord in [i.id for i in channel.guild.premium_subscribers]:
                name = "`✨ " + player.name + "`"
            alts = BOT.db.players.get_alts_by_uuid(player.uuid)
            if alts[0]:
                name += f" (ALTS: {'|'.join([*[i.name for i in alts[0]]])})"
            players.append(RosterPlayer(name, role))

    for role in roles:
        if not [i for i in [j.role.id for j in players] if i == role.id]:
            continue
        if len(messages[-1]) > 1900:
            messages.append("")
        messages[-1] += f"\n## - {role.icon} {role.name}:\n"
        roster = [p for p in players if p.role.id == role.id]

        while len(roster) > 0:
            if len(messages[-1]) > 1900:
                messages.append("")
            while len(roster) > 0 and len(messages[-1]) <= 1900:
                player = roster.pop()
                if messages[-1] and messages[-1][-1] != "\n":
                    messages[-1] += ", "
                messages[-1] += player.name

    if channel.guild.id != 1120419648316395530:
        return [*messages, f"> All rosters are available at: https://discord.gg/77meGgDHQB !"]
    return messages
