import discord
from discord.ext import commands
import random
from helpers.utils import Embed


class UselessCommands(commands.Cog, name='Useless Commands'):
    """All the fun but useless commands"""

    def __init__(self, bot, hidden):
        self.bot = bot
        self.hidden = hidden 
        
    @commands.command()
    async def smh(self, ctx):
        embed = await Embed(ctx.author, description=f'{ctx.author.mention} shakes their head').user_colour()
        await ctx.send(embed=embed)
        
    @commands.command(aliases=["failed", "fail"])
    async def mistake(self, ctx):
        embed = await Embed(ctx.author,
                            description=f"{ctx.author.mention} had an <a:sparkles:932286365008281640> Unintentional failure <a:sparkles:932286365008281640>") \
                      .user_colour()
        await ctx.send(embed=embed)
        
    @commands.command()
    async def f(self, ctx):
        embed = await Embed(ctx.author,
                            description=f"<:press_f:709688246774267905> {ctx.author.mention} has paid their respects") \
                      .user_colour()
        await ctx.send(embed=embed)
        
    @commands.command(aliases=["x"])
    async def doubt(self, ctx):
        await ctx.send("<:Doubt:667984676744331283>")
        
    @commands.command()
    async def gooby(self, ctx):
        gooby = await Embed(ctx.author, title="gooby", description="<:gooby:810130190197719050> gooby").user_colour()
        await ctx.send(embed=gooby)

    @commands.command()
    async def hug(self, ctx, member: discord.Member):
        if member == ctx.author:
            embed = await Embed(ctx.author, description=f"{ctx.author} tried to hug themself",
                                url="https://cdn.discordapp.com/emojis/759485870146584586.png?v=1", color=0x00FF00) \
                .set_footer(text="self love is appreciated").user_colour()
            await ctx.send(embed=embed)
        else:    
            embed = await Embed(ctx.author, description=f"{ctx.author.mention} hugged {member.mention}",
                                url="https://cdn.discordapp.com/emojis/759485870146584586.png?7v=1").user_colour()
            await ctx.send(embed=embed)
    
    @commands.command()
    async def gn(self, ctx, member: discord.Member):
        if member == ctx.author:
            embed = await Embed(ctx.author, description=f"{ctx.author} wished themselves a good sleep",
                                url="https://cdn.discordapp.com/emojis/759485870146584586.png?v=1", color=0x00FF00) \
                .set_footer(text="Goodnight!").user_colour()
            await ctx.send(embed=embed)
        else:    
            embed = await Embed(ctx.author, description=f"{ctx.author.mention} wished {member.mention} happy dreams",
                                url="https://cdn.discordapp.com/emojis/759485870146584586.png?7v=1").user_colour()
            await ctx.send(embed=embed)
    
    @commands.command()
    async def gm(self, ctx, member: discord.Member):
        if member == ctx.author:
            embed = await Embed(ctx.author, description=f"{ctx.author} wished themselves a good morning",
                                url="https://cdn.discordapp.com/emojis/759485870146584586.png?v=1", color=0x00FF00) \
                          .set_footer(text="Good morning!").user_colour()
            await ctx.send(embed=embed)
        else:    
            embed = await Embed(ctx.author,
                                description=f"{ctx.author.mention} blessed {member.mention} with a good morning!",
                                url="https://cdn.discordapp.com/emojis/759485870146584586.png?7v=1").user_colour()
            await ctx.send(embed=embed)
    
    @commands.command()
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
                 f"{stabby} was brutally slain by {gamer}"]
        if member == ctx.author:
            embed = await Embed(ctx.author, description="We do not promote self harm in Nullzee's Cave.").user_colour()
        else:
            embed = await Embed(ctx.author, description=str(random.choice(funny))).user_colour()
        await ctx.send(embed=embed)
    
    @commands.command()
    async def slap(self, ctx, member: discord.Member):
        gamer = ctx.author.mention
        slappy = member.mention
        funny = [f"{slappy} was slapped by {gamer}",
                 f"{gamer} slapped {slappy}",
                 f"{gamer} smacked {slappy} across the face",
                 f"{gamer} hurt {slappy}"]
        if member == ctx.author:
            embed = await Embed(ctx.author, description="We do not promote self harm in Nullzee's Cave.").user_colour()
        else:
            embed = await Embed(ctx.author, description=str(random.choice(funny))).user_colour()
        await ctx.send(embed=embed)
    
    @commands.command()
    async def bonk(self, ctx, member: discord.Member):
        embed = await Embed(ctx.author, description=f"{member.mention} got bonked").user_colour()
        await ctx.send(embed=embed)
    
    @commands.command()
    async def crikey(self, ctx):
        embed = await Embed(ctx.author, title="crikey", description="<:crikey:812430464785580062> crikey").user_colour()
        await ctx.send(embed=embed)
        
    @commands.command()
    async def gg(self, ctx):
        embed = await Embed(ctx.author,
                            title="gg",
                            description="<a:RainbowDancin:856584656799137803> You did something! Congrats! ") \
            .user_colour()
        await ctx.send(embed=embed)
        
    @commands.command()
    async def boop(self, ctx, member: discord.Member):
        embed = await Embed(ctx.author, description=f"<:boop:803398424166137856>{member.mention}").user_colour()
        await ctx.send(embed=embed)
        

def setup(bot):
    bot.add_cog(UselessCommands(bot, False))
