import discord
from discord.ext import commands

class Useless_commands(commands.Cog, name='Useless Commands'):
    def __init__ (self,bot,hidden):
        self.bot = bot
        self.hidden = hidden 

    @commands.command()
    async def f(self,ctx):
        embed = await Embed(description = f'<:press_f:709688246774267905> {ctx.author.mention} has paid their respects').user_colour()
        await ctx.send(embed = embed)

    @commands.command()
    async def hug(self,ctx,member: discord.Member):
        if member == ctx.author:
            await ctx.send(embed=discord.Embed(description = f"{ctx.author} tried to hug themself",
                                               url = "https://cdn.discordapp.com/emojis/759485870146584586.png?v=1",
                                               footer='self love is appreciated', color=0x00FF00))
        else:    
            await ctx.send(embed = discord.Embed(description = f"{ctx.author.mention} hugged {member.mention}", url ="https://cdn.discordapp.com/emojis/759485870146584586.png?v=1"))
    
    @commands.command()
    async def stab(member: discord.Member):
        if member ==  ctx.author:
            await ctx.send(embed = discord.Embed(description = "We do not promote self harm in Nullzee's cave."))
        else:
            await ctx.send(embed = discord.Embed(description = f"{ctx.author.mention} caused harm to {member.mention}"))         

def setup(bot):
    bot.add_cog(Useless_commands(bot, False))
