from dataclasses import dataclass

from discord.ext import commands
import discord
import asyncio
import typing

from helpers.constants import Role

LOG_CHANNEL = 760898316405571615

event_perms = commands.has_any_role(Role.EVENT_HOSTER, Role.STAFF, Role.TRAINEE)


@dataclass
class Event:
    owner: discord.Member
    channel: discord.TextChannel
    url: str
    participants: typing.Dict[str, discord.Member]


class Events(commands.Cog, name="events"):

    def __init__(self, bot):
        self.bot: commands.Bot = bot
        self.hidden = False
        self.event: Event = None

    @commands.command()
    @commands.guild_only()
    async def joinEvent(self, ctx: commands.Context):
        if self.event is None:
            return await ctx.send("There is no event active!")
        if ctx.author in self.event.participants.values():
            return await ctx.send("You are already signed up for this event!")
        try:
            dm_channel = (await ctx.author.send("What will your IGN be?")).channel
        except discord.Forbidden:
            return await ctx.send(f"{ctx.author.mention} Please enable DMs from server members")
        check = lambda msg: msg.author.id == ctx.author.id and msg.channel.id == dm_channel.id
        try:
            ign = (await self.bot.wait_for("message", check=check, timeout=60)).content
        except asyncio.TimeoutError:
            return await ctx.author.send("Timed out")

        if ign in self.event.participants:
            return await ctx.author.send("Someone has already registered with this IGN")

        self.event.participants[ign] = ctx.author

        channel = self.event.channel
        channel = channel if channel else self.event.owner
        await channel.send(embed=discord.Embed(colour=discord.Colour.green(),
                                               description=f"{ctx.author.mention} "
                                                           f"({ctx.author}) signed up for the event with the IGN `{ign}`"
                                               ))
        await ctx.author.send(f"You have signed up for the event as `{ign}`. "
                              "Please use the name you selected above or you will be kicked from the game"
                              f"\n{self.event.url}")

    @commands.command()
    @event_perms
    async def startEvent(self, ctx: commands.Context, url: str, channel: discord.TextChannel = None):
        if self.event is not None:
            return await ctx.send("There is already an active event!")
        self.event = Event(ctx.author, channel, url, {})
        await ctx.send("Event started")

    @commands.command()
    @event_perms
    async def endEvent(self, ctx: commands.Context):
        self.event = None
        await ctx.send("Event ended")

    @commands.command()
    @event_perms
    async def eventIgn(self, ctx: commands.Context, ign: str):
        if not self.event:
            return await ctx.send("There is no event active")
        if ign not in self.event.participants:
            return await ctx.send("This IGN is not registered")
        user = self.event.participants[ign]
        await ctx.send(f"{user.mention} ({user}) signed up with this IGN")


def setup(bot):
    bot.add_cog(Events(bot))
