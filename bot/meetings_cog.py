from discord.ext import tasks, commands
from collections import defaultdict
import logging
import os
import json
import aiofiles
import time
import random
import utils

_COG_NAME = "Meetings"
log = logging.getLogger(__name__)

class ScheduleEntry:

    def __init__(self, **kwargs):
        self.time = _format_time(kwargs["hour"], kwargs["minute"])
        self.hour = kwargs.get("hour")
        self.minute = kwargs.get("minute")
        self.fired = 0
        self.guild_id = kwargs.get("guild_id")
        self.channel_id = kwargs.get("channel_id")
        self.author_id = kwargs.get("author_id")


def _format_time(hour: int, minute: int) -> str:
    """Turns hours and minutes to a string with the format 'HH:MM'. Assumes 24h clock"""
    return f"{str(hour).rjust(2, '0')}:{str(minute).rjust(2, '0')}"


def _insert_schedule_entry(schedule, entry) -> bool:
    if len(schedule) >= Meetings.SCHEDULE_LIMIT:
        return False
    elif entry.time in [s.time for s in schedule]:
        return False

    schedule.append(entry)
    schedule.sort(key=lambda x: (x.hour, x.minute))
    return True


class Meetings(commands.Cog, name=_COG_NAME):
    SCHEDULE_LIMIT = 8
    DB_DIR = "data/"
    DB_PATH = DB_DIR + "schedules.json"

    def __init__(self, bot):
        self.bot = bot
        self.schedule_guild = defaultdict(list)
        self.schedule_dm = defaultdict(list)

    async def load_schedules(self):
        def load_list(schedule_group):
            out = defaultdict(list)
            for key in schedule_group:
                for item in schedule_group[key]:
                    entry = ScheduleEntry(**item)
                    out[int(key)].append(entry)
            return out

        if os.path.exists(Meetings.DB_PATH):
            async with aiofiles.open(Meetings.DB_PATH, mode="r") as file:
                file_data = await file.read()
                json_data = json.loads(file_data)
                self.schedule_guild = load_list(json_data["schedule_guild"])
                self.schedule_dm = load_list(json_data["schedule_dm"])

        self._scheduler_task.start()

    async def _write_schedules(self):
        utils.create_folder_if_needed(Meetings.DB_DIR)
        async with aiofiles.open(Meetings.DB_PATH, mode="w+") as file:
            out = {
                "schedule_guild":
                    {key: [vars(value) for value in self.schedule_guild[key]] for key in self.schedule_guild},

                "schedule_dm":
                    {key: [vars(value) for value in self.schedule_dm[key]] for key in self.schedule_dm}
            }
            await file.write(json.dumps(out))

    def get_schedule_entry_channel(self, entry):
        if entry.guild_id:
            channel = self.bot.get_channel(entry.channel_id)
        else:
            user = self.bot.get_user(entry.author_id)
            channel = user.dm_channel if user else None
        return channel

    @tasks.loop(seconds=10.0)
    async def _scheduler_task(self):
        t_now = time.localtime()
        secs_now = time.time()
        schedule_union = list(self.schedule_guild.values())
        schedule_union.extend(self.schedule_dm.values())
        for schedules in schedule_union:
            for entry in schedules:
                should_fire = secs_now - entry.fired > 3600
                if should_fire and t_now.tm_hour == entry.hour and t_now.tm_min == entry.minute:
                    # Event fired
                    entry.fired = secs_now
                    channel = self.get_schedule_entry_channel(entry)
                    if not channel:
                        log.error(f"Channel not found {entry.channel_id}")
                        return
                    if entry.guild_id:
                        await channel.send("Time to meet, @everyone!")
                    else:
                        await channel.send(f"Here's your reminder for "
                                           f"{_format_time(t_now.tm_hour, t_now.tm_min)}.")

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

    def schedule_for_ctx(self, ctx):
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
        except TypeError:
            await ctx.send(f"Didn't understand the time \"{meet_time}."
                           f" Please provide a time like so \"20:30\"")
            return

        channel = ctx.channel
        guild_id = ctx.guild.id if ctx.guild else ctx.guild
        if ctx.guild and ctx.guild.system_channel:
            channel = ctx.guild.system_channel
        daily = ScheduleEntry(hour=hour, minute=minute, guild_id=guild_id,
                              channel_id=channel.id, author_id=ctx.author.id)

        entry_added = _insert_schedule_entry(self.schedule_for_ctx(ctx), daily)

        if entry_added:
            await ctx.send(f"Scheduled a daily meeting at {daily.time}")
        else:
            await ctx.send(f"Couldn't schedule. Check if you reached the {Meetings.SCHEDULE_LIMIT} entries limit "
                           f"or if there's already an entry at that time using !showschedule")

        await self._write_schedules()

    @commands.command()
    async def showschedule(self, ctx):
        """Lists all scheduled daily meetings"""
        res = self.schedule_for_ctx(ctx)

        if not res:
            await ctx.send("Our schedule is empty.")
            return

        response_list = []
        for i, entry in enumerate(res):
            channel = self.get_schedule_entry_channel(entry)
            response_list.append(f"[{i}] {entry.time} on #{str(channel)}")

        newline = "\n"
        await ctx.send(f"Here's our schedule:\n{newline.join(response_list)}")

    # TODO: Delete Schedule entry
    # TODO: Schedule with subcommands
