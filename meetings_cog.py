from discord.ext import tasks, commands
import time
import random

_COG_NAME = "Meetings"


class Schedule:

    def __init__(self, time_str, guild_channel):
        self.time_str = time_str
        self.hour, self.minute = [int(n) for n in time_str.split(":")]
        self.fired = 0
        self.channel = guild_channel


class Meetings(commands.Cog, name=_COG_NAME):

    def __init__(self, bot):
        self.bot = bot
        self.schedule = []
        self._task_schedule.start()

    @tasks.loop(seconds=10.0)
    async def _task_schedule(self):
        # print(f"ten seconds passed: {time.strftime('%S:%M:%H', time.localtime())}")
        t_now = time.localtime()
        t_secs = time.time()
        for s in self.schedule:
            should_fire = t_secs - s.fired > 3600
            if should_fire and t_now.tm_hour == s.hour and t_now.tm_min == s.minute:
                s.fired = t_secs
                await s.channel.send("Time to meet, @everyone!")

    @commands.command(description="Randomly chooses an order for users in a voice channel to take turns.")
    async def startmeeting(self, ctx):
        """Chooses an order for people in your voice channel talk"""
        if not ctx.author.voice:
            await ctx.send("Please join the voice channel where the meeting will take place first.")
            return
        participants = ctx.author.voice.channel.members
        meeting_order = [p.name for p in random.sample(participants, len(participants))]
        await ctx.send(" -> ".join(meeting_order))

    @commands.command(description="It's pretty much self explanatory")
    async def calleveryone(self, ctx):
        """Mention @everyone"""
        if not ctx.guild:
            await ctx.send(f"What's the purpose of calling everyone here, huh, {ctx.author.mention}?")
        else:
            await ctx.send("Hey @everyone I think a meeting is about to start!")

    @commands.command(description="Sets an alarm that goes off every day at the specified time hh:mm, "
                                  "ex. !schedulemeeting 9:30")
    async def scheduledaily(self, ctx, meet_time):
        """Schedule a daily meeting at time hh:mm"""
        try:
            hour, minute = [int(n) for n in meet_time.split(":")]
        except:
            await ctx.send(f"Didn't understand the time \"{meet_time}\"\n"
                           f"please provide a time like \"20:30\"")
            return

        daily = Schedule(meet_time, ctx.channel)
        self.schedule.append(daily)
        await ctx.send(f"Scheduled a daily meeting at {hour}:{minute}")

    @commands.command()
    async def showschedule(self, ctx):
        """Lists all scheduled daily meetings"""
        response_list = "\n ".join([f"{s.time_str} on {str(s.channel)}" for s in self.schedule])
        await ctx.send(f"Here's our schedule:\n {response_list}")
