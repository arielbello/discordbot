import utils
from collections import defaultdict
from discord.ext import tasks
import aiofiles
import logging
from datetime import datetime, timedelta
import json
import os

log = logging.getLogger(__name__)


class Constants:
    DB_VERSION_KEY = "version"
    DB_VERSION = "1.0"
    DB_DIR = "data/"
    DB_PATH = DB_DIR + "schedules.json"
    SCHEDULE_LIMIT = 8
    ENTRIES = "entries"
    UTC_OFFSET = "utc_offset"
    DM_LIST = "schedule_dm"
    GUILD_LIST = "schedule_guild"
    FAILSAFE_TIMER = 10


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
    _failsafe_timer = Constants.FAILSAFE_TIMER

    def __init__(self, client):
        self.schedule_dm = defaultdict(dict)
        self.schedule_guild = defaultdict(dict)
        self.client = client

    async def setup_schedule(self):

        def load_list(schedule_group):
            out = defaultdict(dict)
            if not schedule_group:
                return out

            for key in schedule_group:
                out[int(key)] = {Constants.ENTRIES: list()}
                for item in schedule_group[key].get(Constants.ENTRIES):
                    entry = Entry(**item)
                    out[int(key)][Constants.ENTRIES].append(entry)
                out[int(key)][Constants.UTC_OFFSET] = schedule_group[key].get(Constants.UTC_OFFSET)

            return out

        if os.path.exists(Constants.DB_PATH):
            async with aiofiles.open(Constants.DB_PATH, mode="r") as file:
                file_data = await file.read()
                try:
                    json_data = json.loads(file_data)
                    db_version = json_data.get(Constants.DB_VERSION_KEY)
                except json.decoder.JSONDecodeError:
                    print("Empty db or error decoding JSON")
                    self._scheduler_task.start()
                    return

            if db_version != Constants.DB_VERSION:
                json_data = None

            if json_data:
                self.schedule_guild = load_list(json_data.get(Constants.GUILD_LIST))
                self.schedule_dm = load_list(json_data.get(Constants.DM_LIST))

        self._scheduler_task.start()

    async def fire_entries(self, schedule_list, message, hour_interval=0):
        for entry_id in schedule_list:
            entry_info = schedule_list[entry_id]
            utc_offset = entry_info.get(Constants.UTC_OFFSET)
            if utc_offset is None:
                utc_offset = 0
            now = datetime.utcnow() + timedelta(hours=utc_offset)
            secs_now = now.timestamp()
            # Don't even try to fire on Sunday. Everyone deserves some *me time*
            if now.weekday() == 6:
                return
            if Constants.ENTRIES not in entry_info:
                break
            for entry in entry_info[Constants.ENTRIES]:
                should_fire = secs_now - entry.fired > 3600 * 6
                if should_fire and \
                        entry.hour + hour_interval >= now.hour >= entry.hour - hour_interval \
                        and now.minute == entry.minute:
                    # Event fired
                    entry.fired = secs_now
                    channel = self.get_entry_channel(entry)
                    if not channel:
                        log.error(f"Channel not found {entry.channel_id}")
                        return

                    time_str = utils.format_time(entry.hour, entry.minute)
                    await channel.send(message.format(time_str))

    @tasks.loop(seconds=10.0)
    async def _scheduler_task(self):
        await self.fire_entries(self.schedule_guild, "Hey, @everyone! It's time - {}!")
        await self.fire_entries(self.schedule_dm, "Here's your reminder for {}.")
        # Schedule._failsafe_timer -= 10
        # Todo find a way to make this work
        # if Schedule._failsafe_timer <= 0:
        #     await self.fire_entries(self.schedule_guild, "Something came up and I couldn't tell you at {}", 1)
        #     await self.fire_entries(self.schedule_dm, "Something came up and I couldn't fire at {}", 1)
        #     Schedule._failsafe_timer = Constants.FAILSAFE_TIMER

    def get_entry_channel(self, entry):
        if entry.guild_id:
            channel = self.client.bot.get_channel(entry.channel_id)
        else:
            user = self.client.bot.get_user(entry.author_id)
            channel = user.dm_channel if user else None
        return channel

    def get_entry_list(self, ctx):
        if ctx.guild:
            return self.schedule_guild[ctx.guild.id].get(Constants.ENTRIES)
        else:
            return self.schedule_dm[ctx.author.id].get(Constants.ENTRIES)

    def get_entry_dic(self, ctx):
        if ctx.guild:
            return self.schedule_guild[ctx.guild.id]
        else:
            return self.schedule_dm[ctx.author.id]

    def set_timezone(self, ctx, offset):
        entry_dic = self.get_entry_dic(ctx)
        entry_dic[Constants.UTC_OFFSET] = offset

    def get_timezone(self, ctx):
        entry_dic = self.get_entry_dic(ctx)
        return entry_dic.get(Constants.UTC_OFFSET)

    def add_schedule_entry(self, ctx, entry) -> bool:
        entry_dic = self.get_entry_dic(ctx)
        if Constants.ENTRIES not in entry_dic:
            entry_dic[Constants.ENTRIES] = []
        utc_offset = entry_dic.get(Constants.UTC_OFFSET)

        entry_dic[Constants.UTC_OFFSET] = utc_offset
        entries = entry_dic[Constants.ENTRIES]
        if len(entries) >= Constants.SCHEDULE_LIMIT:
            return False
        elif entry.time in [e.time for e in entries]:
            return False

        entries.append(entry)
        entries.sort(key=lambda x: (x.hour, x.minute))
        return True

    async def write_schedules(self):

        def build_entries(schedule_dic):
            return {key:
                        {Constants.ENTRIES:
                             [vars(value) for value in schedule_dic[key][Constants.ENTRIES]
                              if schedule_dic[key].get(Constants.ENTRIES)],

                         Constants.UTC_OFFSET: schedule_dic[key][Constants.UTC_OFFSET]}
                    for key in schedule_dic}

        utils.create_folder_if_needed(Constants.DB_DIR)
        async with aiofiles.open(Constants.DB_PATH, mode="w+") as file:
            out = {
                Constants.DB_VERSION_KEY: Constants.DB_VERSION,

                Constants.GUILD_LIST: build_entries(self.schedule_guild),

                Constants.DM_LIST: build_entries(self.schedule_dm)

            }
            await file.write(json.dumps(out))
