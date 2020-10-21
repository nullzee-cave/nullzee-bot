import discord
from discord.ext import commands

class Useless_commands(commands.Cog, name='Useless Commands'):
    def __init__ (self,bot,hidden):
        self.bot = bot
        self.hidden = hidden 

    @commands.command()
    async def f(self,ctx):
        await ctx.send(f'<:press_f:709688246774267905> {ctx.author.mention} has paid their respects')

    @commands.command()
    async def hug(self,ctx,member: discord.Member):
        await ctx.send(f'<:hug:759485870146584586> {ctx.author.mention} hugged {member.mention}')
    

def setup(bot):
    bot.add_cog(Useless_commands(bot, False))
