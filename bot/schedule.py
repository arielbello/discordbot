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
    DB_VERSION_KEY = "version"
    DB_VERSION = "1.0"
    DB_DIR = "data/"
    DB_PATH = DB_DIR + "schedules.json"
    SCHEDULE_LIMIT = 8
    ENTRIES = "entries"
    UTC_OFFSET = "utc_offset"
    DM_LIST = "schedule_dm"
    GUILD_LIST = "schedule_guild"
    TIMEZONE_ENV = "DISCORD_BOT_TIMEZONE"

    def __init__(self, client):
        self.schedule_dm = defaultdict(dict)
        self.schedule_guild = defaultdict(dict)
        # utc offset in hours
        utc_offset = os.environ.get(Schedule.TIMEZONE_ENV)
        self.utc_offset = utc_offset if utc_offset else 0
        self.client = client

    async def setup_schedule(self):

        def load_list(schedule_group):
            out = {}
            if not schedule_group:
                return None

            for key in schedule_group:
                out[int(key)] = {Schedule.ENTRIES: list()}
                for item in schedule_group[key].get(Schedule.ENTRIES):
                    entry = Entry(**item)
                    out[int(key)][Schedule.ENTRIES].append(entry)
                out[int(key)][Schedule.UTC_OFFSET] = schedule_group[key].get

            return out

        if os.path.exists(Schedule.DB_PATH):
            async with aiofiles.open(Schedule.DB_PATH, mode="r") as file:
                file_data = await file.read()
                try:
                    json_data = json.loads(file_data)
                    db_version = json_data.get(Schedule.DB_VERSION_KEY)
                except json.decoder.JSONDecodeError:
                    print("Empty db or error decoding JSON")
                    self._scheduler_task.start()
                    return

            if db_version != Schedule.DB_VERSION:
                # TODO make update
                pass

            if json_data():
                self.schedule_guild = load_list(json_data.get(Schedule.GUILD_LIST))
                self.schedule_dm = load_list(json_data.get(Schedule.DM_LIST))

        self._scheduler_task.start()
        # self._scheduler_failsafe.start()

    @tasks.loop(seconds=10.0)
    async def _scheduler_task(self):
        t_now = time.gmtime()
        # Don't even try to fire on Sunday. Everyone deserves some *me time*
        if t_now.tm_wday == 6:
            return
        secs_now = time.time()
        schedule_list = self.schedule_dm
        for entry_id in schedule_list:
            entry_info = schedule_list[entry_id]
            utc_offset = entry_info.get(Schedule.UTC_OFFSET)
            if utc_offset is None:
                utc_offset = self.utc_offset
            for entry in entry_info[Schedule.ENTRIES]:
                should_fire = secs_now - entry.fired > 3600
                if should_fire and t_now.tm_hour == entry.hour + utc_offset and t_now.tm_min == entry.minute:
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

    @tasks.loop(seconds=125)
    async def _scheduler_failsafe(self):
        # TODO implement
        pass

    def get_entry_channel(self, entry):
        if entry.guild_id:
            channel = self.client.bot.get_channel(entry.channel_id)
        else:
            user = self.client.bot.get_user(entry.author_id)
            channel = user.dm_channel if user else None
        return channel

    def get_entry_list(self, ctx):
        if ctx.guild:
            return self.schedule_guild[ctx.guild.id].get(Schedule.ENTRIES)
        else:
            return self.schedule_dm[ctx.author.id].get(Schedule.ENTRIES)

    def get_entry_dic(self, ctx):
        if ctx.guild:
            return self.schedule_guild[ctx.guild.id]
        else:
            return self.schedule_dm[ctx.author.id]

    def add_schedule_entry(self, ctx, entry) -> bool:
        entry_dic = self.get_entry_dic(ctx)
        if not entry_dic:
            entry_dic[Schedule.ENTRIES] = []
        utc_offset = entry_dic.get(Schedule.UTC_OFFSET)
        if not utc_offset:
            utc_offset = self.utc_offset
            entry_dic[Schedule.UTC_OFFSET] = utc_offset

        entry_list = entry_dic[Schedule.ENTRIES]
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
                Schedule.DB_VERSION_KEY: Schedule.DB_VERSION,

                Schedule.GUILD_LIST:
                    {key:
                         {Schedule.ENTRIES: [vars(value) for value in self.schedule_guild[key][Schedule.ENTRIES]],
                          Schedule.UTC_OFFSET: self.schedule_guild[key][Schedule.UTC_OFFSET]}
                     for key in self.schedule_guild},

                Schedule.DM_LIST:
                    {key:
                         {Schedule.ENTRIES: [vars(value) for value in self.schedule_dm[key][Schedule.ENTRIES]],
                          Schedule.UTC_OFFSET: self.schedule_dm[key][Schedule.UTC_OFFSET]}
                     for key in self.schedule_dm}
            }
            await file.write(json.dumps(out))
