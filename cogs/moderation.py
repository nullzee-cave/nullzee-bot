from discord.ext import commands, tasks
import typing
from random import randint
from helpers.utils import stringToSeconds as sts, Embed, TimeConverter
import json
import asyncio
import discord
from helpers import payloads, moderationUtils
from api_key import moderationColl

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
        await user.send(f"You were banned from {ctx.guild.name} {f'for `{_time}`' if _time else ''} {f'for `{reason}`' if reason else ''}")
        await user.ban(reason=reason)
        await moderationColl.insert_one(payload)
        await ctx.send(embed=moderationUtils.chatEmbed(ctx, payload))
        await moderationUtils.log(self.bot, payload)

    @commands.command()
    @commands.has_guild_permissions(manage_messages=True)
    async def unban(self,ctx,*,member):
        banned_users = await ctx.guild.bans()
        member_name, member_discriminator = member.split("#")
        for bans in banned_users:
            user = bans.user
            if (user.name, user.discriminator) == (member_name, member_discriminator):
                await ctx.guild.unbann(user)
                embed = discord.Embed(title = "Member was unbanned", description = f"{user} was unbanned")
                logchannel = ctx.guild.get_channel(667957285837864960)
                await logchannel.send(embed=embed)


    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def purge(self, ctx, limit:int):
        def check(m):
            return not m.pinned
        await ctx.channel.purge(limit=limit + 1, check=check)
        await asyncio.sleep(1)
        chatembed = discord.Embed(description=f"Cleared {limit} messages", color=0xfb00fd)
        chatembed.set_author(name=ctx.author, icon_url=ctx.author.avatar_url)
        await ctx.send(embed=chatembed)
        logembed = discord.Embed(title="Purge", description=f"{limit} messages cleared from {ctx.channel.mention}")
        logembed.set_author(name=ctx.author, icon_url=ctx.author.avatar_url)
        logchannel = ctx.guild.get_channel(667957285837864960)
        await logchannel.send(embed=logembed)




def setup(bot):
    bot.add_cog(Moderation(bot, True))
