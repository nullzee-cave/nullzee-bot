from discord.ext import commands
import discord
from api_key import userColl
from helpers.utils import get_user, getFileJson, saveFileJson
from perks.perkSystem import PerkConverter, perk_list
from perks import perks


class Points(commands.Cog):
    def __init__(self, bot, hidden):
        self.bot: commands.Bot = bot
        self.hidden = hidden

    @commands.command()
    async def shop(self, ctx, item: PerkConverter = None):
        user = await get_user(ctx.author)
        if not item:
            string = ""
            for perk in perk_list:
                string += f"{perk.name}:  `{perk.cost} points`\n"
            return await ctx.send(embed=discord.Embed(title=f"Shop - {user['points']} points", description=string, color=0x00FF00) \
                                  .set_footer(text="purchase a perk with -purchase [perk name]"))
        else:
            return await ctx.send(embed=discord.Embed(
                title=f"Shop page for {item.name}",
                description=f"\n\nName: {item.name}\n\nDescription: {item.description}\n\nPrice: `{item.cost} points`\n\nAliases: {', '.join(item.aliases)}",
                color=0x00FF00))

    @commands.command(aliases=["buy", "redeem", "claim"])
    @commands.guild_only()
    async def purchase(self, ctx, item: PerkConverter, *, arg=None):
        user = await get_user(ctx.author)
        if item.require_arg and not arg:
            return await ctx.send(embed=discord.Embed(title="Error!", description="You need to specify an argument for this perk!", colour=0xFF0000))
        if user["points"] >= item.cost:
            await item.on_buy(ctx, arg)
            await userColl.update_one({"_id": str(ctx.author.id)}, {"$inc": {"points": -item.cost}})
            await ctx.send(f"successfully bought `{item.name}` for `{item.cost}` points")
        else:
            return await ctx.send("You cannot afford this!")

    @commands.command()
    @commands.has_guild_permissions(manage_messages=True)
    async def changePoints(self, ctx, user: discord.Member, points: int):
        await userColl.update_one({"_id": str(user.id)}, {"$inc": {"points": points}})
        await ctx.send(f"changed {user.mention}'s points by {points}")


def setup(bot):
    bot.add_cog(Points(bot, False))
