import discord
from discord.ext import commands

@commands.command()
async def f(self,ctx):
    await ctx.send('press_f')
    await ctx.send(f'{ctx.author.mention} has paid their respects')

def setup(bot):
    bot.add_cog(usless_commands(bot, True))