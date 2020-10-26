from discord.ext import commands, tasks
from random import randint
from helpers.utils import stringToSeconds as sts, Embed
import json
import asyncio
import discord
import aiohttp
import random
from discord.ext.commands.cooldowns import BucketType
import time
import math
import ast
import datetime

class moderation(commands.Cog, name="Moderation"):
    def __init__(self, bot, hidden):
        self.hidden = hidden
        self.bot = bot


    @commands.command()
    @commands.has_guild_permissions(manage_messages=True)
    async def qotd(self, ctx):
        with open('config.json') as f:
            config = json.load(f)
        config["qotd"] = (datetime.datetime.now() - datetime.datetime.utcfromtimestamp(0)).days
        with open('config.json', 'w') as f:
            json.dump(config, f)
        await ctx.send("Last QOTD time set to now")


    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def purge(self, ctx, limit:int):
        def check(m):
            return not m.pinned
        await ctx.channel.purge(limit=limit + 1, check=check)
        await asyncio.sleep(1)
        chatembed = discord.Embed(description=f"Cleared {limit} messages", color=0xfb00fd)
        chatembed.set_author(name=ctx.author, icon_url=ctx.author.avatar_url)
        await ctx.send(embed=chatembed)
        logembed = discord.Embed(title="Purge", description=f"{limit} messages cleared from {ctx.channel.mention}")
        logembed.set_author(name=ctx.author, icon_url=ctx.author.avatar_url)
        logchannel = ctx.guild.get_channel(667957285837864960)
        await logchannel.send(embed=logembed)


    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def slowmode(self, ctx, time="off"):
        if time.lower() == "off":
            await ctx.channel.edit(slowmode_delay=0)
            return await ctx.send(f"slowmode has been removed from {ctx.channel.mention} by {ctx.author.mention}")
        else:
            timer = sts(time)
            if not timer:
                return await ctx.send("invalid slowmode time")
            else:
                await ctx.channel.edit(slowmode_delay=timer)
                return await ctx.send(f"slowmode has been set to `{time}` by {ctx.author.mention}")


    @commands.command()
    #@commands.has_guild_permissions(manage_messages=True)
    @commands.has_any_role("Staff", "Trainee Staff")
    async def role(self, ctx, user:discord.Member, *, role:str):
        rolelist = {z.name.lower() : z.id for z in ctx.guild.roles}
        abbreviations = {"vc lord": 682656964123295792, "godly giveaway donator": 681900556788301843}
        if role.lower() in rolelist:
            role = ctx.guild.get_role(rolelist[role.lower()])
            if role.permissions.manage_messages:
                await ctx.send("You are not allowed to give that role")
                return
            try:
                await user.add_roles(role)
            except discord.Forbidden:
                await ctx.send("I am not allowed to assign that role to that user")
                return
            chatembed = discord.Embed(title="Role added :scroll:", description=f":white_check_mark: Gave {role.mention} to {user.mention}", color=0xfb00fd)
            #chatembed.set_thumbnail(url="https://media1.tenor.com/images/ff7606164243cc6032f5769b5c5b76cd/tenor.gif?itemid=16266330")
            # role = discord.utils.get(ctx.guild.roles, name=role)
            await ctx.send(embed=chatembed)
            await ctx.message.delete()
            return
        elif role.lower() in abbreviations:
            role = ctx.guild.get_role(abbreviations[role])
            try:
                await user.add_roles(role)
            except discord.Forbidden:
                await ctx.send("I am not allowed to assign that role to that user")
                return
            chatembed = discord.Embed(title="Role added :scroll:", description=f":white_check_mark: Gave {role.mention} to {user.mention}", color=0xfb00fd)
            await ctx.send(embed=chatembed)
            await ctx.message.delete()
            return
        else:
            embed = discord.Embed(title=":x: Adding role failed", description=f"Correct Usage: `-role <@user> <rolename>`", color=0xff0000)
            embed.set_author(name=ctx.author, icon_url=ctx.author.avatar_url)
            await ctx.send(embed=embed)
            return

        # try:
        #     await user.add_roles(role)
        # except discord.Forbidden:
        #     await ctx.send("I am not allowed to assign that role to that user")
        #     return
        # chatembed = discord.Embed(title="Role added :scroll:", description=f":white_check_mark: Gave {role.mention} to {user.mention}", color=0xfb00fd)
        # #chatembed.set_thumbnail(url="https://media1.tenor.com/images/ff7606164243cc6032f5769b5c5b76cd/tenor.gif?itemid=16266330")


    @commands.command()
    #@commands.has_guild_permissions(manage_roles=True)
    @commands.has_any_role("Staff")
    async def removerole(self, ctx, user:discord.Member, *, role:str):
        rolelist = {z.name.lower() : z.id for z in ctx.guild.roles}
        if role.lower() in rolelist:
            role = ctx.guild.get_role(rolelist[role.lower()])
            if role.permissions.administrator or role.permissions.manage_messages:
                await ctx.send("You are not allowed to remove that role")
                return
            try:
                await user.remove_roles(role)
            except discord.Forbidden:
                await ctx.send("I am not allowed to remove that role from that user")
                return
            chatembed = discord.Embed(title="Role removed :scroll:", description=f":white_check_mark: removed {role.mention} from {user.mention}", color=0xfb00fd)
            #chatembed.set_thumbnail(url="https://media1.tenor.com/images/ff7606164243cc6032f5769b5c5b76cd/tenor.gif?itemid=16266330")
            # role = discord.utils.get(ctx.guild.roles, name=role)
            await ctx.send(embed=chatembed)
            await ctx.message.delete()
            return
        else:
            embed = discord.Embed(title=":x: removing role failed", description=f"Correct Usage: `-removerole <@user> <rolename>`", color=0xff0000)
            embed.set_author(name=ctx.author, icon_url=ctx.author.avatar_url)
            await ctx.send(embed=embed)
            return

        # try:
        #     await user.add_roles(role)
        # except discord.Forbidden:
        #     await ctx.send("I am not allowed to assign that role to that user")
        #     return
        # chatembed = discord.Embed(title="Role added :scroll:", description=f":white_check_mark: Gave {role.mention} to {user.mention}", color=0xfb00fd)
        # #chatembed.set_thumbnail(url="https://media1.tenor.com/images/ff7606164243cc6032f5769b5c5b76cd/tenor.gif?itemid=16266330")



    @commands.command(aliases=["star", "pin"])
    @commands.has_guild_permissions(manage_messages=True)
    async def starboard(self, ctx: commands.Context, _id: int, *, title:str=""):
        msg: discord.Message = await ctx.channel.fetch_message(_id)
        embed = (await Embed(msg.author, title=f"{title} | {ctx.channel.name}", description=msg.content, url=msg.jump_url).auto_author().timestamp_now().user_colour()).set_footer(text=f"starred by {ctx.author}")
        if msg.attachments:
            embed.set_image(url=msg.attachments[0].url)
        star_message = await ctx.guild.get_channel(770316631829643275).send(embed=embed)
        await ctx.send(embed=await Embed(ctx.author, title="Added to starboard!", url=star_message.jump_url).user_colour())


    def insert_returns(self, body):
        # insert return stmt if the last expression is a expression statement
        if isinstance(body[-1], ast.Expr):
            body[-1] = ast.Return(body[-1].value)
            ast.fix_missing_locations(body[-1])
    @commands.command(name="eval", aliases=["eval_fn", "-e"])
    async def eval_fn(self, ctx, *, cmd):
        """Evaluates input.
        Input is interpreted as newline seperated statements.
        If the last statement is an expression, that is the return value.
        Usable globals:
        - `bot`: the bot instance
        - `discord`: the discord module
        - `commands`: the discord.ext.commands module
        - `ctx`: the invokation context
        - `__import__`: the builtin `__import__` function
        Such that `>eval 1 + 1` gives `2` as the result.
        The following invokation will cause the bot to send the text '9'
        to the channel of invokation and return '3' as the result of evaluating
        >eval ```
        a = 1 + 2
        b = a * 2
        await ctx.send(a + b)
        a
        ```
        """
        owners = [564798709045526528]
        if ctx.author.id in owners:
            fn_name = "_eval_expr"

            cmd = cmd.strip("`")

            # add a layer of indentation
            cmd = "\n".join(f"    {i}" for i in cmd.splitlines())

            # wrap in async def body
            body = f"async def {fn_name}():\n{cmd}"

            parsed = ast.parse(body)
            body = parsed.body[0].body

            self.insert_returns(body)

            env = {
                'bot': ctx.bot,
                'discord': discord,
                'commands': commands,
                'ctx': ctx,
                '__import__': __import__
            }
            exec(compile(parsed, filename="<ast>", mode="exec"), env)

            result = (await eval(f"{fn_name}()", env))
            await ctx.send(f"```py\n{result}\n```")





def setup(bot):
    bot.add_cog(moderation(bot, True))
