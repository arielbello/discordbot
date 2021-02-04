from discord.ext import tasks, commands
from collections import defaultdict
import time
import random

_COG_NAME = "Meetings"


class ScheduleEntry:

    def __init__(self, p_hour, p_minute, p_guild, p_channel, p_author):
        self.time = f"{str(p_hour).rjust(2,'0')}:{str(p_minute).rjust(2,'0')}"
        self.hour = p_hour
        self.minute = p_minute
        self.fired = 0
        self.guild = p_guild
        self.channel = p_channel
        self.author = p_author

class Meetings(commands.Cog, name=_COG_NAME):

    SCHEDULE_LIMIT = 8

    def __init__(self, bot):
        self.bot = bot
        self.schedule_guild = defaultdict(list)
        self.schedule_dm = defaultdict(list)
        self._task_schedule.start()

    @tasks.loop(seconds=10.0)
    async def _task_schedule(self):
        # print(f"ten seconds passed: {time.strftime('%S:%M:%H', time.localtime())}")
        t_now = time.localtime()
        t_secs = time.time()
        for s in self.schedule_guild:
            should_fire = t_secs - s.fired > 3600
            if should_fire and t_now.tm_hour == s.hour and t_now.tm_min == s.minute:
                s.fired = t_secs
                await s.channel.send("Time to meet, @everyone!")

    @commands.command(description="Randomly chooses an order for users in a voice channel to take turns.")
    async def startmeeting(self, ctx):
        """Chooses an order for people in your voice channel to talk"""
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
            await ctx.send("Hey @everyone, I think a meeting is about to start!")


    def insert_schedule_entry(self, schedule, entry):

        if len(schedule) >= Meetings.SCHEDULE_LIMIT:
            return False
        elif entry.time in [s.time for s in schedule]:
            return False

        schedule.append(entry)
        schedule.sort(key=lambda x: (x.hour, x.minute))
        return True

    def schedule_list_for(self, ctx):
        if ctx.guild:
            return self.schedule_guild[ctx.guild.id]
        else:
            return self.schedule_dm[ctx.author.id]

    @commands.command(description="Sets an alarm that goes off every day at the specified time hh:mm, "
                                  "ex. !schedulemeeting 9:30")
    async def scheduledaily(self, ctx, meet_time):
        """Schedule a daily meeting at time hh:mm"""
        try:
            hour, minute = [int(n) for n in meet_time.split(":")]
        except:
            await ctx.send(f"Didn't understand the time \"{meet_time}."
                           f" Please provide a time like so \"20:30\"")
            return

        p_channel = ctx.channel
        if ctx.guild and ctx.guild.system_channel:
            p_channel = ctx.guild.system_channel
        daily = ScheduleEntry(hour, minute, ctx.guild, p_channel, ctx.author)

        entry_added = self.insert_schedule_entry(self.schedule_list_for(ctx), daily)

        if entry_added:
            await ctx.send(f"Scheduled a daily meeting at {daily.time}")
        else:
            await ctx.send(f"Couldn't schedule. Check if you reached the {Meetings.SCHEDULE_LIMIT} entries limit "
                           f"or if there's already an entry at that time using !showschedule")

    @commands.command()
    async def showschedule(self, ctx):
        """Lists all scheduled daily meetings"""
        res = self.schedule_list_for(ctx)

        if not res:
            await ctx.send("Our schedule is empty.")
            return

        response_list = "\n".join([f"[{i}] {s.time} on #{str(s.channel)}" for i, s in enumerate(res)])
        await ctx.send(f"Here's our schedule:\n{response_list}")

    # TODO: Delete Schedule entry
