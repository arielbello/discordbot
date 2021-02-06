import discord
from discord.ext import commands
from hacker_cog import Hacker
from meetings_cog import Meetings
import logging
import random
import os


# Basic setup
logging.basicConfig(level=logging.INFO)
description = "I'm trying to help manage this server, specially with meetings."
intents = discord.Intents.default()
# Privileged intent. Without it, getting members information won't work
intents.members = True
bot = commands.Bot(command_prefix="!", description=description, intents=intents)


@bot.event
async def on_ready():
    print('Logged in as')
    print(bot.user.name)
    print(bot.user.id)
    print('------')
    # Time to load saved state from disk
    await bot.cogs["Meetings"].load_schedule()


@bot.event
async def on_message(msg):
    # Required, otherwise commands won't work
    await bot.process_commands(msg)


@bot.event
async def on_command_error(ctx, error):
    """"Handles all errors"""
    print(error)
    line1 = "I'm sorry, Fury. I can't let you do that."
    line2 = "I'm sorry. I can't..."
    line3 = "I can't let you do that, Kung Fury."
    await ctx.send(random.choice([line1, line2, line3]))


token = os.environ["DISCORD_TOKEN"]
bot.add_cog(Hacker(bot))
bot.add_cog(Meetings(bot))
bot.run(token)
