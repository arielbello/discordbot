import discord
from discord.ext import commands
import random
"""
This file is not used.
The commands listed serve as a quick reference on how to use discord.py.
"""
bot = commands.Bot(command_prefix="?", description="Reference of commands", intents=intents)


@bot.command(description="For when you wanna settle the score some other way")
async def choose(ctx, *choices: str):
    """Chooses between multiple choices"""
    await ctx.send(random.choice(choices))


@bot.command()
async def joined(ctx, member: discord.Member):
    """Says when a member joined"""
    await ctx.send('{0.name} joined in {0.joined_at}'.format(member))

@bot.command()
async def members(ctx):
    """Tells the number of members currently in this server"""
    people = ctx.guild.members
    await ctx.send("there are {} devs here!".format(len(people)))


@members.error
async def members_error(ctx, error):
    """Custom command error example"""
    await ctx.send("couldn't process your command " + str(error))