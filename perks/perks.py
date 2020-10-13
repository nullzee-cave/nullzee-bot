from perks.perkSystem import perk, PerkError
from discord.ext import commands
import discord


@perk(name="AskNullzee", description="Ask Nullzee a question!", cost=5, aliases=["NullzeeQuestion", "askNull"])
async def askNullzee(ctx, arg):
    msg = await ctx.guild.get_channel(738350726417219645).send(
        embed=discord.Embed(description=arg, color=0x00FF00)
            .set_author(name=ctx.author, icon_url=ctx.author.avatar_url))
    await ctx.send(embed=discord.Embed(title="Bought!", url=msg.jump_url, color=0x00FF00))
