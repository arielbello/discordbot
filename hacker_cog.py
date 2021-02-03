from discord.ext import commands

_COG_NAME = "H4CK3R"


class Hacker(commands.Cog, name=_COG_NAME):

    def __init__(self, bot):
        self.bot = bot

    @commands.command(description="I'm gonna pong back and tell how fast I did it!")
    async def ping(self, ctx):
        """Test my latency"""
        await ctx.send("Ponged back in just {:.4f} seconds!".format(self.bot.latency))