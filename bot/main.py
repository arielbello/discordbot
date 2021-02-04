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

@bot.command()
async def members(ctx):
    """Tells the number of members currently in this server"""
    people = ctx.guild.members
    print(people)
    await ctx.send("there are {} devs here!".format(len(people)))


@members.error
async def members_error(ctx, error):
    """Custom command error example"""
    await ctx.send("couldn't process your command " + str(error))

# Testing some commands
@bot.command(description="For when you wanna settle the score some other way")
async def choose(ctx, *choices: str):
    """Chooses between multiple choices"""
    await ctx.send(random.choice(choices))


@bot.command()
async def joined(ctx, member: discord.Member):
    """Says when a member joined"""
    await ctx.send('{0.name} joined in {0.joined_at}'.format(member))


token = os.environ["DISCORD_TOKEN"]
bot.add_cog(Hacker(bot))
bot.add_cog(Meetings(bot))
bot.run(token)
