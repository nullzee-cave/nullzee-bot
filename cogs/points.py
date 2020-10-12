from discord.ext import commands
import discord
from api_key import userColl
from helpers.utils import get_user
from perks.perkSystem import PerkConverter, perk_list
from perks import perks


class Points(commands.Cog):
    def __init__(self, bot, hidden):
        self.bot: commands.Bot = bot
        self.hidden = hidden

    @commands.command()
    async def shop(self, ctx, item: PerkConverter = None):
        if not item:
            string = ""
            for perk in perk_list:
                string += f"{perk.name}:  `{perk.cost} points`\n"
            return await ctx.send(embed=discord.Embed(title="Shop", description=string, color=0x00FF00) \
                                  .set_footer(text="purchase a perk with -buy [perk name]"))
        else:
            return await ctx.send(embed=discord.Embed(
                title=f"Shop page for {item.name}",
                description=f"\n\nName: {item.name}\n\nDescription: {item.description}\n\nPrice: `{item.cost} points`\n\nAliases: {', '.join(item.aliases)}",
                color=0x00FF00))

    @commands.command(aliases=["buy", "redeem", "claim"])
    @commands.guild_only()
    async def purchase(self, ctx, item: PerkConverter, *, arg):
        user = await get_user(ctx.author)
        if user["points"] >= item.cost:
            await item.on_buy(ctx, arg)
            await userColl.update_one({"_id": str(ctx.author.id)}, {"$inc": {"points": -item.cost}})
        else:
            return await ctx.send("You cannot afford this!")

def setup(bot):
    bot.add_cog(Points(bot, False))
