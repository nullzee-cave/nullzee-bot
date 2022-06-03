import discord
from discord.ext import commands
from helpers.utils import Embed


class UselessCommands(commands.Cog, name="Useless Commands"):
    """All the fun but useless commands"""

    # TODO: replace emoji links with actual emojis using their ids

    def __init__(self, bot, hidden):
        self.bot = bot
        self.hidden = hidden 
        
    @commands.command()
    async def smh(self, ctx):
        embed = Embed(ctx.author, description=f"{ctx.author.mention} shakes their head")
        await embed.user_colour(self.bot)
        await ctx.send(embed=embed)
        
    @commands.command(aliases=["majoroof", "bigoof"])
    async def oof(self, ctx):
        embed = Embed(ctx.author, description=f"<:robloxbighead:968095802742419496> O O F")
        await embed.user_colour(self.bot)
        await ctx.send(embed=embed)

    @commands.command(aliases=["failed", "fail"])
    async def mistake(self, ctx):
        embed = Embed(ctx.author,
                      description=f"{ctx.author.mention} had an <a:sparkles:932286365008281640> "
                                  f"Unintentional failure <a:sparkles:932286365008281640>")
        await embed.user_colour(self.bot)
        await ctx.send(embed=embed)
        
    @commands.command()
    async def f(self, ctx):
        embed = Embed(ctx.author,
                      description=f"<:press_f:709688246774267905> {ctx.author.mention} has paid their respects")
        await embed.user_colour(self.bot)
        await ctx.send(embed=embed)
        
    @commands.command(aliases=["x"])
    async def doubt(self, ctx):
        await ctx.send("<:Doubt:667984676744331283>")
        
    @commands.command()
    async def gooby(self, ctx):
        embed = Embed(ctx.author, title="gooby", description="<:gooby:810130190197719050> gooby")
        await embed.user_colour(self.bot)
        await ctx.send(embed=embed)

    @commands.command()
    async def hug(self, ctx, member: discord.Member):
        if member == ctx.author:
            embed = Embed(ctx.author, description=f"{ctx.author} tried to hug themself",
                          url="https://cdn.discordapp.com/emojis/759485870146584586.png?v=1")
            embed.set_footer(text="self love is appreciated")
            await embed.user_colour(self.bot)
            await ctx.send(embed=embed)
        else:    
            embed = Embed(ctx.author, description=f"{ctx.author.mention} hugged {member.mention}",
                          url="https://cdn.discordapp.com/emojis/759485870146584586.png?7v=1")
            await embed.user_colour(self.bot)
            await ctx.send(embed=embed)
    
    @commands.command()
    async def gn(self, ctx, member: discord.Member):
        if member == ctx.author:
            embed = Embed(ctx.author, description=f"{ctx.author} wished themselves a good sleep",
                          url="https://cdn.discordapp.com/emojis/759485870146584586.png?v=1")
            embed.set_footer(text="Goodnight!")
            await embed.user_colour(self.bot)
            await ctx.send(embed=embed)
        else:    
            embed = Embed(ctx.author, description=f"{ctx.author.mention} wished {member.mention} happy dreams",
                          url="https://cdn.discordapp.com/emojis/759485870146584586.png?7v=1")
            await embed.user_colour(self.bot)
            await ctx.send(embed=embed)
    
    @commands.command()
    async def gm(self, ctx, member: discord.Member):
        if member == ctx.author:
            embed = Embed(ctx.author, description=f"{ctx.author} wished themselves a good morning",
                          url="https://cdn.discordapp.com/emojis/759485870146584586.png?v=1")
            embed.set_footer(text="Good morning!")
            await embed.user_colour(self.bot)
            await ctx.send(embed=embed)
        else:    
            embed = Embed(ctx.author, description=f"{ctx.author.mention} blessed {member.mention} with a good morning!",
                          url="https://cdn.discordapp.com/emojis/759485870146584586.png?7v=1")
            await embed.user_colour(self.bot)
            await ctx.send(embed=embed)
    
    @commands.command()
    async def bonk(self, ctx, member: discord.Member):
        embed = Embed(ctx.author, description=f"{member.mention} got bonked")
        await embed.user_colour(self.bot)
        await ctx.send(embed=embed)
    
    @commands.command()
    async def crikey(self, ctx):
        embed = Embed(ctx.author, title="crikey", description="<:crikey:812430464785580062> crikey")
        await embed.user_colour(self.bot)
        await ctx.send(embed=embed)
        
    @commands.command()
    async def gg(self, ctx):
        embed = Embed(ctx.author, title="gg",
                      description="<a:RainbowDancin:856584656799137803> You did something! Congrats! ")
        await embed.user_colour(self.bot)
        await ctx.send(embed=embed)
        
    @commands.command()
    async def boop(self, ctx, member: discord.Member):
        embed = Embed(ctx.author, description=f"<:boop:803398424166137856>{member.mention}")
        await embed.user_colour(self.bot)
        await ctx.send(embed=embed)
        

async def setup(bot):
    await bot.add_cog(UselessCommands(bot, False))
