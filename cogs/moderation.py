from discord.ext import commands, tasks
import typing
from random import randint
from helpers.utils import stringToSeconds as sts, Embed, TimeConverter
import json
import asyncio
import discord
from helpers import payloads, moderationUtils
from api_key import moderationColl
import datetime

class Moderation(commands.Cog, name="Moderation"): # moderation commands, warns, mutes etc.
    def __init__(self, bot, hidden):
        self.hidden = hidden
        self.bot = bot


    @commands.command()
    @commands.has_guild_permissions(manage_messages=True)
    async def warn(self, ctx, user: discord.Member, *, reason:str):
        payload = payloads.warn_payload(offender_id=user.id, mod_id=ctx.author.id, reason=reason)
        await moderationColl.insert_one(payload)
        await ctx.send(embed=moderationUtils.chatEmbed(ctx, payload))
        await user.send(f"You were warned in {ctx.guild.name} for {reason}")
        await moderationUtils.log(self.bot, payload)
        await moderationUtils.warn_punishments(ctx, user)

    @commands.command()
    @commands.has_guild_permissions(manage_messages=True)
    async def mute(self, ctx, user: discord.Member, _time: typing.Optional[TimeConverter]=None, *, reason:str=None):
        if user.guild_permissions.manage_messages:
            return await ctx.send("You cannot mute a moderator/administrator")
        payload = payloads.mute_payload(offender_id=user.id, mod_id=ctx.author.id, duration=_time, reason=reason)
        await user.add_roles(ctx.guild.get_role(moderationUtils.MUTED_ROLE))
        await moderationColl.insert_one(payload)
        await ctx.send(embed=moderationUtils.chatEmbed(ctx, payload))
        await moderationUtils.log(self.bot, payload)
        time_string = payload["duration_string"]
        await user.send(f"You were muted in {ctx.guild.name} {f'for `{time_string}`' if _time else ''} {f'for `{reason}`' if reason else ''}")

    @commands.command()
    @commands.has_guild_permissions(manage_messages=True)
    async def unmute(self, ctx, user:discord.Member, *, reason:str=None):
        await moderationColl.delete_many({"offender_id": user.id, "type": "mute"})
        await user.remove_roles(ctx.guild.get_role(moderationUtils.MUTED_ROLE))
        await moderationUtils.end_log(self.bot, {"type": "mute", "offender_id": user.id}, moderator=ctx.author, reason=reason)
        await ctx.send(embed=discord.Embed(description=f"unmuted {user}", colour=discord.Colour.green()))


    @commands.command()
    @commands.has_guild_permissions(manage_messages=True)
    async def ban(self, ctx, user: discord.Member, _time: typing.Optional[TimeConverter], *, reason:str=None):
        if user.guild_permissions.manage_messages:
            return await ctx.send("You cannot ban a moderator/administrator")
        payload = payloads.ban_payload(offender_id=user.id, mod_id=ctx.author.id, duration=_time, reason=reason)
        time_string = payload["duration_string"]
        try:
            await user.send(f"You were banned from {ctx.guild.name} {f'for `{time_string}`' if _time else ''} {f'for `{reason}`' if reason else ''}")
        except discord.Forbidden:
            pass
        await user.ban(reason=reason)
        await moderationColl.insert_one(payload)
        await ctx.send(embed=moderationUtils.chatEmbed(ctx, payload))
        await moderationUtils.log(self.bot, payload)

    @commands.command()
    @commands.has_guild_permissions(manage_messages=True)
    async def unban(self, ctx, member, *, reason:str=None):
        try:
            await ctx.guild.unban(moderationUtils.BannedUser(member))
        except (discord.NotFound, discord.HTTPException):
            return await ctx.send("Could not find a ban for that user")
        await moderationUtils.end_log(self.bot, {"type": "ban", "offender_id": member}, moderator=ctx.author, reason=reason)
        await ctx.send(embed=discord.Embed(description=f"**{member} was unbanned**", color=discord.Colour.green()))


    @commands.command()
    @commands.has_guild_permissions(manage_messages=True)
    async def delwarn(self, ctx, _id:str):
        doc = await moderationColl.find_one({"id": _id})
        if not doc:
            return await ctx.send("Could not find that warning")
        else:
            await moderationColl.update_one(doc, {"$set": {"expired": True}})
            await ctx.send("Successfully deleted warning `{}`".format(_id))

    @commands.command()
    async def warnings(self, ctx, user:discord.Member=None):
        user = user if user else ctx.author
        warnings = [z async for z in moderationColl.find({"offender_id": user.id, "expired": False})]
        embed = discord.Embed(title=f"{len(warnings)} warnings", colour=discord.Colour.green())
        embed.set_author(name=user, icon_url=user.avatar_url)
        for warning in warnings:
            embed.add_field(name=f"ID: {warning['id']} | {ctx.guild.get_member(warning['mod_id'])}", value=f"{warning['reason']} - {datetime.datetime.fromtimestamp(warning['timestamp']).strftime('%d/%m/%Y, %H:%M:%S')}")
        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Moderation(bot, True))
