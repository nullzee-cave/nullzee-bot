from discord.ext import commands, tasks
from random import randint
from helpers.utils import stringToSeconds as sts, Embed
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
        await ctx.send(embed=discord.Embed(title=f"{user} has been warned", description=reason, colour=0xF7FF00))
        await moderationUtils.log(self.bot, payload)


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
