import json
import os
import random
import time
from datetime import datetime

import discord
import traceback

import httpx

from bot.__utils__ import get_icon, get_name, print_roster, strip_name
from src.main import BOT


class Command:
    def __init__(self, message: discord.Message, args: list[str]):
        self.message = message
        self.args = args

    async def __reply__(self, *messages: str):
        await self.message.reply(
            embed=discord.Embed(
                description="\n".join(messages)[:4094],
                color=discord.Color.from_rgb(254, 63, 63),
            ).set_footer(
                text=f"Requested by @{get_name(self.message.author)}",
                icon_url=get_icon(self.message.author),
            ),
            mention_author=False,
        )

    async def __embed__(self, embed: discord.Embed):
        await self.message.reply(
            embed=embed.set_footer(
                text=f"Requested by @{get_name(self.message.author)}",
                icon_url=get_icon(self.message.author),
            ),
            mention_author=False,
        )

    def require_permission(self, level: str):
        permitted = []
        match level:
            case "root":
                permitted = BOT.db.perm_level.root
            case "manager":
                permitted = [*BOT.db.perm_level.manager, *BOT.db.perm_level.root]
            case "anyone":
                return False
        return self.message.author.id not in permitted

    async def error(self):
        print(self.message.channel)
        await self.message.add_reaction("🙈")

    async def run(self, cmd: str):
        try:
            await getattr(self, f"command_{cmd}", self.error)()
        except Exception as e:
            traceback.print_exc()
            return await self.__reply__(
                f"**Error**: " + str(e).replace("*", "\\*").replace("_", "\\_")
            )

    async def command_help(self):
        """
        @HELP
        :return:
        """
        if self.require_permission("anyone"):
            return await self.error()

        await self.__reply__(
            "### Gideon: Help",
            f"- :small_blue_diamond: `{BOT.prefix}help` — Prints this message.",
            f"- :small_blue_diamond: `{BOT.prefix}whois [--reveal]` — Find player's information from their IGN. `["
            f"--reveal]` to show hidden alts (only for root).",
            f"- :small_blue_diamond: `{BOT.prefix}link <id|slug|mention> <minecraft_ign> <clan_name> <clan_role> [--alt] [<main_ign>] [--hidden]` — Link player.",
            f"- :small_blue_diamond: `{BOT.prefix}unlink <minecraft_ign>` — Unlink player.",
            f"- :small_blue_diamond: `{BOT.prefix}sync [--overwrite]` — Sync database with discord servers. Use --overwrite to replace members' usernames to match Minecraft ones",
            f"- :small_blue_diamond: `{BOT.prefix}refresh` — Sync this server's roster channels with database.",
            f"- :small_blue_diamond: `{BOT.prefix}update` — Update player names from Mojang API.",
            f"- :small_blue_diamond: `{BOT.prefix}backup` — Create a backup of the database.",
            f"- :small_blue_diamond: `{BOT.prefix}roles <clan_name>` — Show roles of a clan.",
            f"- :small_blue_diamond: `{BOT.prefix}gen <amount|clan>` — Attempt to generate link-commands for people in the current guild.",
            f"- :small_blue_diamond: `{BOT.prefix}size <clan_name|all>` — Get the size of a clan / all clans.",
            f"- :small_blue_diamond: `{BOT.prefix}ask <anything>` — Ask the bot a question.",
            f"- :small_blue_diamond: `{BOT.prefix}fetch <guild name>` — Fetch all members from a guild name.",
            f"- :small_blue_diamond: `{BOT.prefix}gideon` — Update the home guild.",
            f"- :small_blue_diamond: `{BOT.prefix}members` — Dump all players into a file.",
        )

    async def command_whois(self):
        if self.require_permission("anyone") or len(self.args) < 1:
            return await self.error()

        if self.args[0].startswith("<@") and self.args[0].endswith(">"):
            player = BOT.db.players.find_by_discord(int(self.args[0][2:-1]))
        else:
            player = BOT.db.players.find_by_ign(self.args[0])
        if player is None:
            return await self.__reply__(
                f"Couldn't find player named `{self.args[0]}`, or their account is hidden!"
            )

        reveal = False
        if len(self.args) > 1 and self.args[1].lower() == "--reveal":
            if self.require_permission("root"):
                return await self.error()
            reveal = True

        if player.hidden and not reveal:
            return await self.__reply__(
                f"Couldn't find player named `{self.args[0]}`, or their account is hidden!"
            )

        alts = BOT.db.players.get_alts_by_uuid(player.uuid)
        private_alts = (
            [i.name for i in alts[1]]
            if reveal
            else [f"+ {len(alts[1])} Hidden"]
            if len(alts[1]) != 0
            else []
        )

        [
            await self.__embed__(
                discord.Embed(
                    description="\n".join(
                        [
                            f"## {player.name}",
                            f"- **Discord**: <@{BOT.db.players.find_by_uuid(auto_player).auto_discord()}> (`{BOT.db.players.find_by_uuid(auto_player).auto_slug()}`)",
                            f"- **UUID**: `{player.uuid}`",
                            f"- **Name is up-to-date as of**: <t:{round(player.last_updated)}:R>",
                            f"- **Visit**: [NameMC](https://namemc.com/profile/{player.uuid}), [Laby](https://laby.net/@{player.uuid})",
                            (
                                f"- **Alts**: `"
                                + (
                                    ", ".join(
                                        [*[i.name for i in alts[0]], *private_alts]
                                    )
                                    or "---"
                                )
                                + "`"
                            )
                            if not player.parents
                            else (
                                f"- **Main accounts**: `{', '.join([i.name for i in player.resolve_parent()])}`"
                            ),
                            f"## Clans"
                            + (
                                "\n> :warning: **This is a shared alt.** Displaying clans of all players who "
                                "use it."
                                if player.parents and len(player.parents) > 1
                                else ""
                            ),
                            *player.print_clans(),
                        ]
                    ),
                )
                .set_image(
                    url=f"https://api.mineatar.io/body/full/{player.uuid}?overlay=true"
                )
                .set_thumbnail(
                    url=get_icon(
                        await BOT.fetch_user(
                            BOT.db.players.find_by_uuid(auto_player).auto_discord()
                        )
                    )
                )
            )
            for auto_player in player.parents or [player.uuid]
        ]

    async def command_roles(self):
        if self.require_permission("anyone") or len(self.args) < 1:
            return await self.error()

        clan = BOT.db.clans.find(self.args[0].lower())
        if not clan:
            return await self.__reply__(f"Can't find clan named '{self.args[0]}'")

        await self.__reply__(
            f"# Roles of {self.args[0]}:\n"
            + "\n".join([f"{role.icon} {role.name}" for role in clan.roles.__list__()])
        )

    async def command_link(self):
        if self.require_permission("manager") or len(self.args) < 2:
            return await self.error()

        if self.args[0].startswith("<@") and self.args[0].endswith(">"):
            member = await BOT.fetch_user(int(self.args[0][2:-1]))
        elif self.args[0].isnumeric():
            member = await BOT.fetch_user(int(self.args[0]))
        else:
            member = [
                member
                for member in self.message.guild.members
                if self.args[0].lower() in member.display_name.lower()
            ]
            if not member:
                return await self.__reply__(
                    f"Couldn't find such member on this server! Specify their display name, ID or mention them."
                )
            member = member[0]

        main: str | None = None
        hidden = False

        clan = BOT.db.clans.find(self.args[2].lower())
        if not clan:
            return await self.__reply__("The specified clan isn't valid!")

        role = [
            r
            for r in clan.roles.__list__()
            if r.name.lower() == self.args[3].replace("_", " ").lower()
        ]
        if not role:
            return await self.__reply__("The specified role isn't valid!")

        if len(self.args) > 5 and self.args[4] == "--alt":
            player = BOT.db.players.find_by_ign(self.args[5])
            if not player:
                return await self.__reply__("The specified alt isn't valid!")
            main = player.uuid

        if len(self.args) > 6 and self.args[6] == "--hidden":
            hidden = True

        async with httpx.AsyncClient(timeout=None) as client:
            response = await client.get(
                f"https://api.mojang.com/users/profiles/minecraft/{self.args[1]}"
            )

            if response.status_code == 200:
                data = response.json()
                player = BOT.db.players.find_by_uuid(data.get("id"))
                if player:
                    BOT.db.players.update(player.uuid, member.id if not main else -1, clan.id, role[0].id)
                else:
                    BOT.db.players.add(
                        parents=[main] if main else None,
                        uuid=data.get("id"),
                        name=data.get("name"),
                        hidden=hidden,
                        _discord=member.id if not main else -1,
                        _slug=f"@{get_name(member)}" if not main else "",
                        clan={
                            "clan": clan.id,
                            "primary": True,
                            "role": role[0].id,
                        },
                    )
                await self.__reply__(f"Successfully added: `{data.get('name')}`")
            elif response.status_code == 429:
                await self.__reply__(
                    "Try again later. Mojang is rate-limiting the bot!"
                )
            else:
                await self.__reply__(
                    f"Couldn't find such player named `{self.args[1]}`! ```",
                    f"gd:link {member.id} NAME {clan.name} {role[0].name.replace(' ', '_')}"
                    f"```",
                )

    async def command_unlink(self):
        if self.require_permission("root") or len(self.args) < 1:
            return await self.error()
        player = BOT.db.players.find_by_ign(self.args[0])
        if not player:
            return await self.__reply__("Couldn't find such account!")

        BOT.db.players.delete(player.uuid)
        await self.__reply__("Player was unlinked!")

    async def command_backup(self):
        if self.require_permission("root"):
            return await self.error()

        os.makedirs(os.path.join(BOT.path, "backups"), exist_ok=True)
        name = f"{len(os.listdir(os.path.join(BOT.path, 'backups')))}-backup_{datetime.now().strftime('%d-%B-%Y')}.json"
        with open(os.path.join(BOT.path, "backups", name), "w") as fp:
            json.dump(BOT.db.__export__(), fp, indent=4)
        return await self.__reply__(
            f"Saved backup as: `{name}` ({round(os.path.getsize(os.path.join(BOT.path, 'backups', name)) / 1024, 2)} KB)"
        )

    async def command_members(self):
        if self.require_permission("root"):
            return await self.error()

        os.makedirs(os.path.join(BOT.path, "exports"), exist_ok=True)
        name = f"{len(os.listdir(os.path.join(BOT.path, 'exports')))}-discord_members.md"
        with open(os.path.join(BOT.path, "exports", name), "w") as fp:
            for guild in BOT.guilds:
                fp.writelines([f"# {guild.name} | {guild.id}\n", "| name | id | roles |\n", "| --- | --- | --- |\n"])
                fp.writelines([f"| {str(member).replace('|', '/')} `{member.display_name.replace('|', '/')}` | {member.id} | {', '.join(['[' + r.name.replace('|', '/') + ' + ' + str(r.id) + ']' for r in member.roles if r.name != '@everyone'])}|\n" for member in guild.members])
                fp.writelines(["\n\n\n"])
        return await self.__reply__(
            f"Saved export as: `{name}` ({round(os.path.getsize(os.path.join(BOT.path, 'exports', name)) / 1024, 2)} KB)"
        )

    async def command_gen(self):
        if (
            self.require_permission("root")
            or len(self.args) < 1
        ):
            return await self.error()

        if self.args[0].isnumeric():
            guild = None
            size = min(int(self.args[0]), 32)
        else:
            guild = [g for g in BOT.guilds if self.args[0].lower() in g.name.lower()][0]
            size = 32
        if guild:
            clan = BOT.db.find_clan(guild.id)
        else:
            clan = BOT.db.find_clan(self.message.guild.id)
        if not clan:
            return await self.__reply__("This guild doesn't belong to any clan!")

        result = []
        members = []
        mention = len(self.args) > 1 and self.args[1] == "--pretty"
        autosend = len(self.args) > 1 and self.args[1] == "--auto"
        staff = len(self.args) > 1 and self.args[1] == "--staff"
        guild_members = self.message.guild.members if not guild else guild.members
        guild_members.sort(key=lambda _: random.randint(0, 100_000))
        for i in range(size):
            for member in guild_members:
                ign = strip_name(member)
                if (
                    member.bot
                    or BOT.db.players.find_by_ign(ign) is not None
                    or member.id in members
                    or BOT.db.players.find_by_discord(member.id)
                ):
                    continue
                members.append(member.id)
                role = BOT.db.get_role(clan.roles, member)
                if not role and not staff:
                    result.append(f":warning: {member.mention} {', '.join([r.name + '|' + str(r.id) for r in member.roles])}!")
                elif not role and staff:
                    continue
                elif role.name == "Offline" or role.name == "Unverified":
                    continue
                else:
                    print(role.name.lower())
                    if staff and not [ii for ii in ["leader", "staff", "mod", "helper", "owner", "found", "officer", "recruit"] if ii in role.name.lower()]:
                        continue
                    if mention:
                        result.append(
                            f"{member.id} {member.mention} ({role.icon} {role.name})".replace(
                                "_", "\\_"
                            )
                        )
                    else:
                        result.append(
                            f"gd:link {member.id} {ign} {clan.name} {role.name.replace(' ', '_')}".replace(
                                "_", "\\_"
                            )
                        )
                break
        if autosend:
            return await self.message.channel.send(
                "\n".join([i.replace("\\", "") for i in result])
            )
        await self.__reply__(*result)

    async def command_size(self):
        if self.require_permission("anyone") or len(self.args) < 1:
            return await self.error()

        do_leak = (
            not self.require_permission("root")
            and len(self.args) > 1
            and self.args[1] == "--guilds"
        )
        if do_leak:
            leak = [
                "### From:",
                *[
                    f"- {guild.name} ({guild.id}) [{guild.icon.url}]"
                    for guild in BOT.guilds
                ],
            ]
        else:
            leak = []

        if self.args[0].lower() == "all":
            return await self.__reply__(
                f"Global number of registered players: {len(BOT.db.players.__list__())}/{sum([g.member_count for g in BOT.guilds])}",
                *leak,
            )

        clan = BOT.db.clans.find(self.args[0].lower())
        if not clan:
            return await self.__reply__("Couldn't find such clan!")

        await self.__reply__(
            f"{clan.name}'s number of registered players: {len([i for i in BOT.db.players.__list__() if clan.id in [j.resolve_clan().id for j in i.clans.__list__()]])}/{BOT.get_guild(clan.guild).member_count}"
        )

    # DISABLED:
    async def command__ask(self):
        if self.require_permission("anyone") or len(self.args) < 1:
            return await self.error()

        await self.message.reply(
            random.choice(["no. ", "yes. ", "maybe. ", "sure. "])
            + random.choice(BOT.memory).replace("@", "\\@")
        )

    async def command_update(self):
        if self.require_permission("root"):
            return await self.error()

        await self.message.add_reaction("☑️")
        updated_count = 0
        BOT.db.players.sort()

        while updated_count < len(BOT.db.players.__list__()):
            async with httpx.AsyncClient(timeout=None) as client:
                BOT.db.players.sort()
                try:
                    print(
                        f"--> https://api.mojang.com/user/profile/{BOT.db.players.__list__()[0].uuid}"
                    )
                    response = await client.get(
                        f"https://api.mojang.com/user/profile/{BOT.db.players.__list__()[0].uuid}"
                    )
                    if response.status_code == 200:
                        BOT.db.players.set(0, response.json().get("name"))
                        updated_count += 1
                        BOT.db.save()
                    else:
                        return await self.__reply__(
                            f"### Exit on {response.status_code}!",
                            f"> Updated {updated_count}/{len(BOT.db.players.__list__())} players.",
                            f"> Least up-to-date account is <t:{round(BOT.db.players.__list__()[0].last_updated)}:R>.",
                        )
                except httpx.ConnectTimeout:
                    BOT.db.players.sort()
                    return await self.__reply__(
                        f"### Exit on CONNECTION_TIMEOUT!",
                        f"> Updated {updated_count}/{len(BOT.db.players.__list__())} players.",
                        f"> Least up-to-date account is <t:{round(BOT.db.players.__list__()[0].last_updated)}:R>.",
                        f"> Most up-to-date account is <t:{round(BOT.db.players.__list__()[-1].last_updated)}:R>.",
                    )
        BOT.db.players.sort()
        await self.__reply__(
            f"Updated all players. Latest update is <t:{round(BOT.db.players.__list__()[0].last_updated)}:R>"
        )

    async def command_fetch(self):
        if self.require_permission("root") or len(self.args) < 1:
            return await self.error()

        target = None
        for guild in BOT.guilds:
            if self.args[0].lower() in guild.name.lower():
                target = guild
                break

        if not target:
            return await self.message.add_reaction("🚫")

        response = []
        for index, member in enumerate(target.members, start=1):
            response.append(
                f"{index}. "
                + member.display_name.replace("_", "\\_")
                + f" `{member}` | `{'' if not member.roles else member.roles[-1].name}`"
            )
        await self.__embed__(
            discord.Embed(
                title=f"{target.name} ({target.member_count})",
                description="\n".join(response)[:3999],
            ).set_thumbnail(url="" if not target.icon else target.icon.url)
        )

    async def command_sync(self):
        if self.require_permission("manager"):
            return await self.error()

        clan = BOT.db.find_clan(self.message.guild.id)
        if not clan:
            return await self.__reply__("This guild doesn't belong to any clan!")

        overwritten = 0
        failed = []
        overwrite = len(self.args) > 0 and self.args[0] == "--overwrite"
        for member in self.message.guild.members:
            if member.id == 465886354941673473 or member.bot:
                continue

            player = BOT.db.players.find_by_discord(member.id)
            role = BOT.db.get_role(clan.roles, member)

            if player:
                if role:
                    BOT.db.players.modify_by_uuid(player.uuid, clan.id, role.id)
                else:
                    failed.append(member.mention)

            if overwrite:
                if not player or player.name in member.display_name:
                    continue

                if not strip_name(member):
                    continue
                __split = member.display_name.split(strip_name(member))
                overwritten += 1
                print(f"--> {__split[0]}{player.name}{__split[1]}")
                try:
                    await member.edit(nick=f"{__split[0]}{player.name}{__split[1]}")
                except discord.errors.Forbidden:
                    await self.__reply__(f"Error, can't rename {player.name} ({member.display_name})")
        await self.__reply__(
            f"Synced the database! {overwritten} named overwritten.\nFailed: {', '.join(failed)}"
        )

    async def command_refresh(self):
        if self.require_permission("manager"):
            return await self.error()

        print(f"Refreshing {self.message.guild.name}")
        clan = BOT.db.find_clan(self.message.guild.id)
        if not clan:
            return await self.__reply__("This guild doesn't belong to any clan!")

        roster_channels = [c for c in self.message.guild.text_channels if "roster" in c.name.lower()]
        if not roster_channels:
            channel = await self.message.guild.create_text_channel(name=f"🔥-roster", overwrites={
                self.message.guild.default_role: discord.PermissionOverwrite(
                    send_messages=False,
                    add_reactions=False,
                    view_channel=True,
                    read_messages=True,
                    read_message_history=True,
                ),
                BOT.user: discord.PermissionOverwrite(
                    send_messages=True,
                    embed_links=True,
                    attach_files=True,
                    manage_messages=True,
                    manage_threads=True,
                    send_messages_in_threads=True,
                    view_channel=True,
                    read_messages=True,
                    read_message_history=True,
                ),
            })
        elif len(roster_channels) > 1:
            channel = roster_channels[0]
            for c in roster_channels:
                if "clan" in c.name:
                    channel = c
                    break
        else:
            channel = roster_channels[0]

        BOT.db.players.sort()
        messages = await print_roster(
            BOT.db.players.__list__()[0].last_updated,
            BOT.db.clan_relations,
            clan.id,
            clan,
            channel,
            BOT.db.clans,
            [
                i
                for i in BOT.db.players.__list__()
                if clan.id in [j.resolve_clan().id for j in i.clans.__list__()]
            ],
            BOT
        )
        history = (
            await channel.history(limit=100, oldest_first=True)
            .filter(lambda m: m.author.id == BOT.user.id)
            .flatten()
        )
        i = 0
        for message in history:
            if i >= len(messages):
                break
            await message.edit(content=messages[i])
            i += 1
        for message in messages[i:]:
            await channel.send(content=message)
            i += 1
        [await m.delete() for m in history[i:]]
        await self.__reply__(f"Updated {clan.name}!")

    async def command_gideon(self):
        if self.require_permission("root"):
            return await self.error()

        guild = BOT.get_guild(BOT.db.home)
        if not guild:
            return await self.error()

        for clan_index, clan in enumerate(BOT.db.clans.__list__()):
            await self.__reply__(f"Updating... {clan.name} ({clan_index + 1})!")
            if not [c for c in guild.text_channels if clan.name.lower() in c.name.lower()]:
                channel = await guild.create_text_channel(name=f"⭐-{clan.name.lower()}", overwrites={
                    guild.default_role: discord.PermissionOverwrite(
                        send_messages=False,
                        add_reactions=False,
                        view_channel=True,
                        read_messages=True,
                        read_message_history=True,
                    ),
                    BOT.user: discord.PermissionOverwrite(
                        send_messages=True,
                        embed_links=True,
                        attach_files=True,
                        manage_messages=True,
                        manage_threads=True,
                        send_messages_in_threads=True,
                        view_channel=True,
                        read_messages=True,
                        read_message_history=True,
                    ),
                })
            else:
                channel = [
                    c for c in guild.text_channels if clan.name.lower() in c.name
                ][0]

            BOT.db.players.sort()
            print(f"{clan.name} --> Generating roster...")
            messages = await print_roster(
                BOT.db.players.__list__()[0].last_updated,
                BOT.db.clan_relations,
                clan_index,
                clan,
                channel,
                BOT.db.clans,
                [
                    i
                    for i in BOT.db.players.__list__()
                    if clan.id in [j.resolve_clan().id for j in i.clans.__list__()]
                ],
                BOT
            )
            print(f"{clan.name} --> Printing...")
            history = (
                await channel.history(limit=100, oldest_first=True)
                .filter(lambda m: m.author.id == BOT.user.id)
                .flatten()
            )
            i = 0
            for message in history:
                if i >= len(messages):
                    break
                await message.edit(content=messages[i])
                i += 1
            for message in messages[i:]:
                await channel.send(content=message)
                i += 1
            if history[i:]:
                [await m.delete() for m in history[i:]]
            print(f"{clan.name} --> Continuting...")
            await self.__reply__(f"Updated {clan.name} ({clan_index+1})!")
