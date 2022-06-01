from dataclasses import dataclass

from discord.ext import commands
import discord
import asyncio
import typing

from helpers.constants import Role, Misc
from helpers.utils import role_ids, list_one


def event_perms(ctx):
    if not ctx.guild or ctx.guild.id != Misc.GUILD:
        return False
    roles = role_ids(ctx.author.roles)
    return list_one(roles, Role.EVENT_HOSTER, Role.ADMIN, Role.STAFF, Role.TRAINEE)


event_perms_check = commands.check(event_perms)


@dataclass
class Event:
    """
    An Event

    For discord based events

    Attributes:
    owner (discord.Member): the person who started the event
    channel (discord.TextChannel): the channel where the event was started
    arg (str): anything else about the event, could be the name of the event, a skribbl.io link, etc
    participants (typing.Dict[str, discord.Member]): a dict of ign:user
    """
    owner: discord.Member
    channel: discord.TextChannel
    arg: str
    participants: typing.Dict[str, discord.Member]


class Events(commands.Cog, name="Events"):
    """All commands related to events that are hosted in Nullzee's Cave"""

    def __init__(self, bot):
        self.bot: commands.Bot = bot
        self.hidden = False
        self.event: Event = None

    @commands.command(name="joinevent")
    @commands.guild_only()
    async def join_event(self, ctx: commands.Context):
        """Join a currently running event"""

        def check(msg):
            return msg.author.id == ctx.author.id and msg.channel.id == dm_channel.id

        if self.event is None:
            return await ctx.send("There is no event active!")
        if ctx.author in self.event.participants.values():
            return await ctx.send("You are already signed up for this event!")
        try:
            dm_channel = (await ctx.author.send("What will your IGN be?")).channel
        except discord.Forbidden:
            return await ctx.send(f"{ctx.author.mention} Please enable DMs from server members")
        try:
            ign = (await self.bot.wait_for("message", check=check, timeout=60)).content
        except asyncio.TimeoutError:
            return await ctx.author.send("Timed out")

        if ign in self.event.participants:
            return await ctx.author.send("Someone has already registered with this IGN")

        self.event.participants[ign] = ctx.author

        channel = self.event.channel
        channel = channel if channel else self.event.owner
        embed = discord.Embed(colour=discord.Colour.green(),
                              description=f"{ctx.author.mention} "
                                          f"({ctx.author}) signed up for the event with the IGN `{ign}`")
        await channel.send(embed=embed)
        await ctx.author.send(f"You have signed up for the event as `{ign}`. "
                              "Please use the name you selected above or you will be kicked from the game"
                              f"\n{self.event.arg}")

    @commands.command(name="startevent")
    @event_perms_check
    async def start_event(self, ctx: commands.Context, arg: str, channel: discord.TextChannel = None):
        """Start a new event"""
        if self.event is not None:
            return await ctx.send("There is already an active event!")
        self.event = Event(ctx.author, channel, arg, {})
        await ctx.send("Event started")

    @commands.command(name="endevent")
    @event_perms_check
    async def end_event(self, ctx: commands.Context):
        """End a currently running event"""
        self.event = None
        await ctx.send("Event ended")

    @commands.command(name="eventign")
    @event_perms_check
    async def event_ign(self, ctx: commands.Context, ign: str):
        """Check which user signed up with a specific ign"""
        if not self.event:
            return await ctx.send("There is no event active")
        if ign not in self.event.participants:
            return await ctx.send("This IGN is not registered")
        user = self.event.participants[ign]
        await ctx.send(f"{user.mention} ({user}) signed up with this IGN")


def setup(bot):
    bot.add_cog(Events(bot))
