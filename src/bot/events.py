import json
import time

import discord

from src.main import BOT
from .__utils__ import get_icon, get_name
from .commands import Command


def filter_memory(message: discord.Message):
    if message.author.bot:
        return False

    if not message.content:
        return False

    if len(message.content) > 128:
        return False

    return True


@BOT.event
async def on_connect():
    print(f"--> Logged-in as {BOT.user}")


@BOT.event
async def on_ready():
    BOT.ready_status = True
    print(f"--> Bot is now ready!")
    with open("memory.json", "r") as fp:
        BOT.memory = json.load(fp).get("memory")

    await BOT.change_presence(activity=discord.Game(name="with its source code"))
    # for guild in BOT.guilds:
    #     print(guild.name)
    #     for role in guild.roles:
    #         print(f"--> {len(role.members)} | {role.id} | {role.name}")


@BOT.event
async def on_message(message: discord.Message):
    for line in message.content.split("\n"):
        if not line.lower().startswith(BOT.prefix) or len(line) == 1:
            continue
        __split = (
            line[3:].replace("  ", " ").replace("  ", " ").replace("  ", " ").split(" ")
        )
        cmd, args = __split[0], __split[1:]
        await Command(message, args).run(cmd)
