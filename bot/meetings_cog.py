from schedule import Schedule, Entry
from discord.ext import commands
import logging
import random

_COG_NAME = "Meetings"
log = logging.getLogger(__name__)


class Meetings(commands.Cog, name=_COG_NAME):

    def __init__(self, bot):
        self.bot = bot
        self.schedule = Schedule(self)

    async def load_schedule(self):
        await self.schedule.setup_schedule()

    @commands.group(description="Meetings top level command")
    async def meeting(self, ctx):
        """[start] - Manage meetings using subcommands"""
        if ctx.invoked_subcommand is None:
            await ctx.send("Do you mean _!meeting start_ ?")

    @meeting.command(name="start")
    async def start_meeting(self, ctx):
        """Chooses an order for people in your voice channel to talk"""
        try:
            voice = ctx.author.voice
        except AttributeError:
            await ctx.send("Trying to start a meeting with yourself?")
            return

        if not voice:
            await ctx.send("Please join the voice channel where the meeting will take place first.")
            return

        participants = ctx.author.voice.channel.members
        meeting_order = [p.name for p in random.sample(participants, len(participants))]
        sep_str = " -> "
        await ctx.send(f"_{sep_str.join(meeting_order)}_")

    def entry_display_string(self, entry, idx=None):
        channel = self.schedule.get_entry_channel(entry)
        entry_str = f"{entry.time} on #{str(channel)}"
        return f"[{idx}] {entry_str}" if idx is not None else entry_str

    @commands.group(description="Top level command for schedule entries")
    async def schedule(self, ctx):
        """[add, list, del, clear] - Manage schedule using subcommands"""
        if ctx.invoked_subcommand is None:
            await ctx.send("Tell me what you want: add, del, list or clear?")

    @schedule.command(name="list", aliases=["show"], description="List all schedule entries with respective indexes")
    async def show_schedule(self, ctx):
        """Lists all scheduled daily meetings (24-hour clock)"""
        res = self.schedule.get_entry_list(ctx)

        if not res:
            await ctx.send("Our schedule is empty.")
            return

        response_list = []
        for i, entry in enumerate(res):
            response_list.append(self.entry_display_string(entry, i))

        newline = "\n"
        await ctx.send(f"Here's our schedule:\n{newline.join(response_list)}")

    @schedule.command(name="add", description="Schedules a message mentioning @everyone. Goes off every day "
                                              "(except Sunday) at the specified time hh:mm, ex. !schedule add 9:30.")
    async def schedule_add(self, ctx, meet_time):
        """Sets a daily alarm to hh:mm (24h clock)"""
        try:
            hour, minute = [int(n) for n in meet_time.split(":")]
        except TypeError:
            await ctx.send(f"Didn't understand the time \"{meet_time}."
                           f" Please provide a time like so \"20:30\" (24-hour clock)")
            return

        channel = ctx.channel
        guild_id = ctx.guild.id if ctx.guild else ctx.guild
        if ctx.guild and ctx.guild.system_channel:
            channel = ctx.guild.system_channel
        daily = Entry(hour=hour, minute=minute, guild_id=guild_id,
                      channel_id=channel.id, author_id=ctx.author.id)

        entry_added = self.schedule.insert_schedule_entry(ctx, daily)

        if entry_added:
            await ctx.send(f"Scheduled a daily meeting at {daily.time}")
        else:
            await ctx.send(f"Couldn't schedule. Check if you reached the {Schedule.SCHEDULE_LIMIT} entries limit "
                           f"or if there's already an entry at that time using !schedule list")

        await self.schedule.write_schedules()

    @schedule.command(name="clear", description="Same as !schedule del all")
    async def schedule_clear(self, ctx):
        await self.delete(ctx, index="all")

    @schedule.command(name="del", aliases=["delete"],
                      description="You can see the entries indexes with !schedule list")
    async def delete(self, ctx, index=None):
        """Delete a schedule entry by index"""
        if not index:
            await ctx.send("C'mon, tell me the index of the entry to be deleted.")
            return

        entries_list = self.schedule.get_entry_list(ctx)
        if not entries_list:
            await ctx.send("You got nothing scheduled to delete.")
            return

        if isinstance(index, str) and index.lower() == "all":
            entries_count = len(entries_list)
            del entries_list[:]
            await self.schedule.write_schedules()
            await ctx.send(f"Deleted {entries_count} stuff from your schedule! Hope you meant to do that!")
            return

        try:
            index = int(index)
        except TypeError:
            await ctx.send("Give me a number as index.")
            return

        if index >= len(entries_list) or index < 0:
            await ctx.send(f"This is not a valid index.")
        else:
            entry_str = self.entry_display_string(entries_list[index])
            del entries_list[index]
            await self.schedule.write_schedules()
            await ctx.send(f"Deleted {entry_str}")
