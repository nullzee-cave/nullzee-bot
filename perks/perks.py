from perks.perkSystem import Perk, register_perk
from discord.ext import commands
import discord


class AskNullzee(Perk):

    def __init__(self):
        self.name = "AskNullzee"
        self.aliases = ["NullzeeQuestion", "askNull"]
        self.description = "Ask Nullzee a question!"
        self.cost = 5

    async def on_buy(self, ctx: commands.Context, arg):
        msg = await ctx.guild.get_channel(738350726417219645).send(
            embed=discord.Embed(description=arg, color=0x00FF00)
                .set_author(name=ctx.author, icon_url=ctx.author.avatar_url))
        await ctx.send(embed=discord.Embed(title="Bought!", url=msg.jump_url, color=0x00FF00))


register_perk(AskNullzee())
