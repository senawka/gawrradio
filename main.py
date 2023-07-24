#!/usr/bin/env python3

import discord
from discord.ext import commands
import asyncio
import json
import random

def load_config():
    with open('config.json') as config_file:
        return json.load(config_file)

async def start_bot():
    bot = commands.Bot(command_prefix=',', intents=discord.Intents.all(), help_command=None)
    config = load_config()
    bot.config = config
    await bot.load_extension('cogs.music_cog')
    return bot

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    bot = loop.run_until_complete(start_bot())

    with open('token.txt') as t:
        token = t.read()
    bot.run(token)
