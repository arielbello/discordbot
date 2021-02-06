import utils
from discord.ext import tasks
from collections import defaultdict
import aiofiles
import logging
import time
import json
import os

log = logging.getLogger(__name__)


class Entry:

    def __init__(self, **kwargs):
        self.time = utils.format_time(kwargs["hour"], kwargs["minute"])
        self.hour = kwargs.get("hour")
        self.minute = kwargs.get("minute")
        self.fired = 0
        self.guild_id = kwargs.get("guild_id")
        self.channel_id = kwargs.get("channel_id")
        self.author_id = kwargs.get("author_id")


class Schedule:

    DB_DIR = "data/"
    DB_PATH = DB_DIR + "schedules.json"
    SCHEDULE_LIMIT = 8

    def __init__(self, client):
        self.schedule_dm = defaultdict(list)
        self.schedule_guild = defaultdict(list)
        self.client = client

    async def setup_schedule(self):
        def load_list(schedule_group):
            out = defaultdict(list)
            for key in schedule_group:
                for item in schedule_group[key]:
                    entry = Entry(**item)
                    out[int(key)].append(entry)
            return out

        if os.path.exists(Schedule.DB_PATH):
            async with aiofiles.open(Schedule.DB_PATH, mode="r") as file:
                file_data = await file.read()
                json_data = json.loads(file_data)
                self.schedule_guild = load_list(json_data["schedule_guild"])
                self.schedule_dm = load_list(json_data["schedule_dm"])

        self._scheduler_task.start()

    @tasks.loop(seconds=10.0)
    async def _scheduler_task(self):
        t_now = time.localtime()
        # Don't even try to fire on Sunday. Everyone deserves some *me time*
        if t_now.tm_wday == 6:
            return
        secs_now = time.time()
        schedule_union = list(self.schedule_guild.values())
        schedule_union.extend(self.schedule_dm.values())
        for schedules in schedule_union:
            for entry in schedules:
                should_fire = secs_now - entry.fired > 3600
                if should_fire and t_now.tm_hour == entry.hour and t_now.tm_min == entry.minute:
                    # Event fired
                    entry.fired = secs_now
                    channel = self.get_entry_channel(entry)
                    if not channel:
                        log.error(f"Channel not found {entry.channel_id}")
                        return

                    time_str = utils.format_time(t_now.tm_hour, t_now.tm_min)
                    if entry.guild_id:
                        await channel.send(f"Hey, @everyone! It's time - {time_str}!")
                    else:
                        await channel.send(f"Here's your reminder for {time_str}.")

    def get_entry_channel(self, entry):
        if entry.guild_id:
            channel = self.client.bot.get_channel(entry.channel_id)
        else:
            user = self.client.bot.get_user(entry.author_id)
            channel = user.dm_channel if user else None
        return channel

    def get_entry_list(self, ctx):
        if ctx.guild:
            return self.schedule_guild[ctx.guild.id]
        else:
            return self.schedule_dm[ctx.author.id]

    def insert_schedule_entry(self, ctx, entry) -> bool:
        entry_list = self.get_entry_list(ctx)
        if len(entry_list) >= Schedule.SCHEDULE_LIMIT:
            return False
        elif entry.time in [e.time for e in entry_list]:
            return False

        entry_list.append(entry)
        entry_list.sort(key=lambda x: (x.hour, x.minute))
        return True

    async def write_schedules(self):
        utils.create_folder_if_needed(Schedule.DB_DIR)
        async with aiofiles.open(Schedule.DB_PATH, mode="w+") as file:
            out = {
                "schedule_guild":
                    {key: [vars(value) for value in self.schedule_guild[key]] for key in self.schedule_guild},

                "schedule_dm":
                    {key: [vars(value) for value in self.schedule_dm[key]] for key in self.schedule_dm}
            }
            await file.write(json.dumps(out))
