import discord
from discord.ext import commands
import random
from helpers.utils import Embed

class Useless_commands(commands.Cog, name='Useless Commands'):
    def __init__ (self,bot,hidden):
        self.bot = bot
        self.hidden = hidden 
        
    @commands.command()
    async def smh(self,ctx):
        embed = await Embed(ctx.author, description = f'{ctx.author.mention} shakes their head').user_colour()
        await ctx.send(embed = embed)
        
    @commands.command()
    async def f(self,ctx):
        embed = await Embed(ctx.author, description = f'<:press_f:709688246774267905> {ctx.author.mention} has paid their respects').user_colour()
        await ctx.send(embed = embed)

    @commands.command()
    async def hug(self,ctx,member: discord.Member):
        if member == ctx.author:
            embed = await Embed(ctx.author, description = f"{ctx.author} tried to hug themself",
                                               url = "https://cdn.discordapp.com/emojis/759485870146584586.png?v=1", color=0x00FF00).set_footer(text="self love is appreciated").user_colour()
            await ctx.send(embed = embed)
        else:    
            embed = await Embed(ctx.author, description = f"{ctx.author.mention} hugged {member.mention}", url ="https://cdn.discordapp.com/emojis/759485870146584586.png?7v=1").user_colour()
            await ctx.send(embed = embed)
    
    @commands.command(aliases = ["slap"])
    async def stab(self, ctx, member: discord.Member):
        gamer = ctx.author.mention
        stabby = member.mention
        funny = [f"{gamer} caused great harm to {stabby}",
                 f"{gamer} caused suffering to {stabby}",
                 f"{gamer} sent {stabby} to the hospital",
                 f"{gamer} made {stabby} feel great amounts of pain",
                 f"{gamer} stabbed {stabby}",
                 f"{stabby} was stabbed by {gamer}",
                 f"{stabby} got cut down by {gamer}",
                 f"{stabby} got sent to heck by {gamer}",
                 f"{gamer} threw a knife at {stabby}",
                 f"{stabby} got stabby stabby stabbed by {gamer}",
                 f"{gamer} :knife: {stabby}",
                 f"{stabby} wasn't spicy enough for {gamer}",
                 f"{stabby} was brutally slain by {gamer}",
                 f"{stabby} was slapped by {gamer}",
                 f"{gamer} slapped {stabby}",
                 f"{gamer} smacked {stabby} across the face",
                 f"{gamer} hurt {stabby}"]
        if member ==  ctx.author:
            embed = await Embed(ctx.author, description = "We do not promote self harm in Nullzee's Cave.").user_colour()
        else:
            embed = await Embed(ctx.author, description = str(random.choice(funny))).user_colour()
        await ctx.send(embed = embed)
             

    @commands.command()
    async def bonk(self, ctx, member: discord.Member):
        await ctx.send(embed = discord.Embed(description = f"{member.mention} got bonked"))
    
    @commands.command()
    async def crikey(self, ctx):
        await ctx.send(embed = discord.Embed(description = "crikey", footer = "pls dm qwerety#2929 a good crikey emote so the command can be finished"))
        
    @commands.command()
    async def boop(self, ctx, member: discord.Member):
        embed = await Embed(ctx.author, description = f":boop:{member.mention}").user_colour()
        await ctx.send(embed = embed)
        
    async def cog_after_invoke(self, ctx):
        await ctx.message.delete()

def setup(bot):
    bot.add_cog(Useless_commands(bot, False))
