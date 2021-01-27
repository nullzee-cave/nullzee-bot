import discord
import ast
from discord.ext import commands
import json
import time
import datetime
from helpers.utils import stringToSeconds as sts, Embed, TimeConverter
from helpers import moderationUtils
import asyncio
from api_key import moderationColl, userColl
import subprocess
import typing


def insert_returns(body):
    # insert return stmt if the last expression is a expression statement
    if isinstance(body[-1], ast.Expr):
        body[-1] = ast.Return(body[-1].value)
        ast.fix_missing_locations(body[-1])


class Staff(commands.Cog):  # general staff-only commands that don't fit into another category
    def __init__(self, bot, hidden):
        self.hidden = hidden
        self.bot: commands.Bot = bot

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        if guild.id in [667953033929293855]:
            return
        embed = discord.Embed(title=f"UNAUTHORISED GUILD JOIN", colour=discord.Colour.red())
        try:
            embed.add_field(name="guild info",
                            value=f"ID: {guild.id}\nname: {guild.name}\nmembers: {guild.member_count}", inline=False)
            embed.add_field(name="owner", value=f"{guild.owner} ({guild.owner.id})", inline=False)
            embed.add_field(name="invite", value=str(
                await [z for z in guild.channels if isinstance(z, discord.TextChannel)][0].create_invite()),
                            inline=False)
        except:
            pass
        await guild.leave()
        await self.bot.get_user(564798709045526528).send(embed=embed)

    @commands.command(aliases=["say"])
    @commands.has_guild_permissions(manage_messages=True)
    async def send(self, ctx, channel: typing.Optional[discord.TextChannel]=None, *, message:str):
        channel = channel if channel else ctx.channel
        if not ctx.author.permissions_in(channel).send_messages:
            raise commands.MissingPermissions(["manage_messages"])
        msg = await channel.send(message)
        if channel.id != ctx.channel.id:
            await ctx.send(msg.jump_url)
    
    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def reply(self, ctx, message: discord.Message, ping: typing.Optional[bool] = True, *, text: str):
        if not ctx.author.permissions_in(message.channel).send_messages:
            raise commands.MissingPermissions(["manage_messages"])
        msg = await message.reply(content=text, mention_author=ping)
        if message.channel.id != ctx.channel.id:
            await ctx.send(msg.jump_url)

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
    @commands.has_guild_permissions(manage_messages=True)
    async def role(self, ctx, user: discord.Member, *, role: str):
        if role.lower() == "muted":
            return await ctx.send("no.")
        rolelist = {z.name.lower(): z.id for z in ctx.guild.roles}
        abbreviations = {"vc lord": 682656964123295792, "godly giveaway donator": 681900556788301843}
        if role.lower() in rolelist:
            role = ctx.guild.get_role(rolelist[role.lower()])
            if role.permissions.manage_messages or role.permissions.administrator:
                await ctx.send("You are not allowed to give that role")
                return
            try:
                await user.add_roles(role)
            except discord.Forbidden:
                await ctx.send("I am not allowed to assign that role to that user")
                return
            chatembed = discord.Embed(title="Role added :scroll:",
                                      description=f":white_check_mark: Gave {role.mention} to {user.mention}",
                                      color=0xfb00fd)
            # chatembed.set_thumbnail(url="https://media1.tenor.com/images/ff7606164243cc6032f5769b5c5b76cd/tenor.gif?itemid=16266330")
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
            chatembed = discord.Embed(title="Role added :scroll:",
                                      description=f":white_check_mark: Gave {role.mention} to {user.mention}",
                                      color=0xfb00fd)
            await ctx.send(embed=chatembed)
            await ctx.message.delete()
            return
        else:
            embed = discord.Embed(title=":x: Adding role failed",
                                  description=f"Correct Usage: `-role <@user> <rolename>`", color=0xff0000)
            embed.set_author(name=ctx.author, icon_url=ctx.author.avatar_url)
            await ctx.send(embed=embed)
            return

    @commands.command()
    @commands.has_guild_permissions(manage_messages=True)
    async def removerole(self, ctx, user: discord.Member, *, role: str):
        if role.lower() == "muted":
            return await ctx.send("no.")
        rolelist = {z.name.lower(): z.id for z in ctx.guild.roles}
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
            chatembed = discord.Embed(title="Role removed :scroll:",
                                      description=f":white_check_mark: removed {role.mention} from {user.mention}",
                                      color=0xfb00fd)
            await ctx.send(embed=chatembed)
            await ctx.message.delete()
            return
        else:
            embed = discord.Embed(title=":x: removing role failed",
                                  description=f"Correct Usage: `-removerole <@user> <rolename>`", color=0xff0000)
            embed.set_author(name=ctx.author, icon_url=ctx.author.avatar_url)
            await ctx.send(embed=embed)
            return

    @commands.command(aliases=["star", "pin"])
    @commands.has_guild_permissions(manage_messages=True)
    async def starboard(self, ctx: commands.Context, message: discord.Message, *, title: str = ""):
        embed = (await Embed(msg.author, title=f"{title} | #{ctx.channel.name}", description=msg.content,
                             url=msg.jump_url).auto_author().timestamp_now().user_colour()).set_footer(
            text=f"starred by {ctx.author}")
        if msg.attachments:
            embed.set_image(url=msg.attachments[0].url)
        star_message = await ctx.guild.get_channel(770316631829643275).send(embed=embed)
        await ctx.send(
            embed=await Embed(ctx.author, title="Added to starboard!", url=star_message.jump_url).user_colour())

    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def purge(self, ctx, limit: int):
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

            insert_returns(body)

            env = {
                'bot': ctx.bot,
                'discord': discord,
                'commands': commands,
                'ctx': ctx,
                "moderationColl": moderationColl,
                "userColl": userColl,
                '__import__': __import__
            }

            try:
                exec(compile(parsed, filename="<ast>", mode="exec"), env)
                result = (await eval(f"{fn_name}()", env))
                await ctx.send(f"```py\n{result}\n```")
            except Exception as e:
                await ctx.send(f"An exception occurred:```py\n{e}\n```")

    @commands.command(aliases=['-he'])
    async def host_eval(self, ctx, *, args):
        if ctx.author.id in [564798709045526528]:
            await ctx.send(f"```\n{subprocess.check_output(args.split(' ')).decode('utf-8')[:1900]}\n```")

    @commands.command()
    @commands.has_guild_permissions(manage_messages=True)
    async def modhelp(self, ctx):
        bot: commands.Bot = ctx.bot
        mod_cogs = [bot.get_cog(z) for z in bot.cogs]
        mod_cogs = filter(lambda x: x.hidden, mod_cogs)
        embed = discord.Embed(title="Moderation Help!", colour=discord.Colour.gold())
        string = ""
        for cog in mod_cogs:
            cog_string = ""
            for cmd in cog.get_commands():
                cog_string += f"\n`{ctx.prefix}{cmd.name}`"
            string += f"\n**{cog.qualified_name}:**{cog_string}"
        embed.description = string
        await ctx.send(embed=embed)

    @commands.group(invoke_without_command=True)
    @commands.has_guild_permissions(manage_messages=True)
    async def blacklist(self, ctx):
        pass
    @blacklist.command(name="add")
    async def blist_add(self, ctx, member: discord.Member, command: str):
        command = command.replace(ctx.prefix, '')
        await userColl.update_one({"_id": str(member.id)}, {"$addToSet": {"command_blacklist": command}})
        await ctx.send(f"blacklisted `{member}` from using `{ctx.prefix}{command}`")
    @blacklist.command(name="remove")
    async def blist_remove(self, ctx, member: discord.Member, command: str):
        command = command.replace(ctx.prefix, '')
        await userColl.update_one({"_id": str(member.id)}, {"$pull": {"command_blacklist": command}})
        await ctx.send(f"unblacklisted `{member}` from using `{ctx.prefix}{command}`")

    @commands.group(aliases=["-c"])
    @commands.has_guild_permissions(manage_messages=True)
    async def config(self, ctx):
        if not ctx.invoked_subcommand:
            await ctx.send(
                "\n".join([f"- {z.name}{'*' if isinstance(z, commands.Group) else ''}" for z in self.config.commands]))
        else:
            await ctx.send("Successfully updated configuration")
            await moderationUtils.update_config()

    @config.command()
    async def mutedRole(self, ctx, *, role: discord.Role):
        await moderationColl.update_one({"_id": "config"}, {"$set": {"muteRole": role.id}})

    @config.command()
    async def deleteWarnsAfter(self, ctx, _time: TimeConverter):
        await moderationColl.update_one({"_id": "config"}, {"$set": {"deleteWarnsAfter": _time}})

    @config.group(invoke_without_command=True)
    async def punishForWarns(self, ctx):
        await ctx.send("\n".join(
            [f"- {z.name}{'*' if isinstance(z, commands.Group) else ''}" for z in self.punishForWarns.commands]))

    @punishForWarns.command(name="add")
    async def p_add(self, ctx, warns: int, duration: TimeConverter, _type="mute"):
        await moderationColl.update_one({"_id": "config"}, {
            "$set": {"punishForWarns.{}".format(warns): {"type": _type, "duration": duration}}})

    @punishForWarns.command(name="remove")
    async def p_remove(self, ctx, warns: int):
        await moderationColl.update_one({"_id": "config"}, {"$unset": {"punishForWarns.{}".format(warns): ""}})

    @config.group(invoke_without_command=True)
    async def automod(self, ctx):
        await ctx.send(
            "\n".join([f"- {z.name}{'*' if isinstance(z, commands.Group) else ''}" for z in self.automod.commands]))

    @automod.group(invoke_without_command=True)
    async def mentions(self, ctx):
        await ctx.send(
            "\n".join([f"- {z.name}{'*' if isinstance(z, commands.Group) else ''}" for z in self.mentions.commands]))

    @mentions.command(name="punishment")
    async def m_punishment(self, ctx, action: str = "delete"):
        await moderationColl.update_one({"_id": "config"},
                                        {"$set": {"mentions.action": action if action == "warn" else "delete"}})

    @mentions.command()
    async def value(self, ctx, val: int):
        await moderationColl.update_one({"_id": "config"}, {"$set": {"mentions.val": val}})

    @mentions.command(name="allowChannel")
    async def m_allowChannel(self, ctx, channel: discord.TextChannel):
        await moderationColl.update_one({"_id": "config"}, {"$push": {"mentions.allowed_channels": channel.id}})

    @mentions.command(name="disallowChannel")
    async def m_disallowChannel(self, ctx, channel: discord.TextChannel):
        await moderationColl.update_one({"_id": "config"}, {"$pull": {"mentions.allowed_channels": channel.id}})

    @automod.group(invoke_without_command=True)
    async def invites(self, ctx):
        await ctx.send(
            "\n".join([f"- {z.name}{'*' if isinstance(z, commands.Group) else ''}" for z in self.invites.commands]))

    @invites.command(name="punishment")
    async def i_punishment(self, ctx, action: str = "delete"):
        await moderationColl.update_one({"_id": "config"},
                                        {"$set": {"invites.action": action if action == "warn" else "delete"}})

    @invites.command(name="allowChannel")
    async def i_allowChannel(self, ctx, channel: discord.TextChannel):
        await moderationColl.update_one({"_id": "config"}, {"$push": {"invites.allowed_channels": channel.id}})

    @invites.command(name="disallowChannel")
    async def i_disallowChannel(self, ctx, channel: discord.TextChannel):
        await moderationColl.update_one({"_id": "config"}, {"$pull": {"invites.allowed_channels": channel.id}})

    @automod.group(invoke_without_command=True)
    async def badWords(self, ctx):
        await ctx.send(
            "\n".join([f"- {z.name}{'*' if isinstance(z, commands.Group) else ''}" for z in self.badWords.commands]))

    @badWords.command(name="add")
    async def b_add(self, ctx, word: str, action: str = "delete"):
        await moderationColl.update_one({"_id": "config"}, {"$set": {"badWords.{}".format(word.lower()): action}})

    @badWords.command(name="remove")
    async def b_remove(self, ctx, word: str):
        await moderationColl.update_one({"_id": "config"}, {"$unset": {"badWords.{}".format(word.lower()): ""}})

    # whiteListedServers = ["667953033929293855","722421169311187037"]
    #
    # @config.group(invoke_without_command = True)
    # async def allowed_guilds(self, ctx):
    #     await ctx.send("\n".join([f"- {z.name}{'*' if isinstance(z, commands.Group) else ''}" for z in self.allowed_guilds.commands]))
    # @allowed_guilds.command(name="add")
    # async def g_add(self,ctx, id: int):
    #     await whiteListedServers.append(id)
    # @allowed_guilds.command(name="remove")
    # async def g_remove(self,ctx, id: int):
    #     await whiteListedServers.remove(id)

    @commands.group(invoke_without_command=True)
    async def sbinfo(self, ctx, category: str):
        try:
            _id = (await moderationColl.find_one({"_id": "config"}))["sbinfoMessages"][category.lower()]
        except KeyError:
            return await ctx.send("Could not find that category")
        url = f"https://discord.com/channels/667953033929293855/788162727461781504/{_id}"
        await ctx.send(
            embed=discord.Embed(title=category, description=f"Click [here]({url}) to view info about {category}",
                                colour=0x00ff00, url=url))

    @sbinfo.command()
    @commands.guild_only()
    @commands.has_any_role(788183123136741426, 667953757954244628)
    async def newCategory(self, ctx: commands.Context, name: str, *, description: str = None):
        msg: discord.Message = await ctx.guild.get_channel(788162727461781504).send(
            embed=discord.Embed(title=name, description=description, colour=0x00FF00))
        await moderationColl.update_one({"_id": "config"}, {"$set": {f"sbinfoMessages.{name.lower()}": msg.id}})
        await ctx.send("Successfully created category")
        await ctx.message.delete()

    @sbinfo.command(name="add")
    @commands.guild_only()
    async def sbi_add(self, ctx: commands.Context, category: str, name: str, *, description: str):
        try:
            _id = (await moderationColl.find_one({"_id": "config"}))["sbinfoMessages"][category.lower()]
        except KeyError:
            return await ctx.send("Could not find that category")
        msg: discord.Message = await ctx.guild.get_channel(788162727461781504).fetch_message(_id)
        await msg.edit(embed=msg.embeds[0].add_field(name=name, value=description, inline=False))
        await ctx.send("Done!")
        await ctx.message.delete()

    @sbinfo.command(name="edit")
    @commands.guild_only()
    @commands.has_any_role(788183123136741426, 667953757954244628)
    async def sbi_edit(self, ctx, category: str, param: str, *, value):
        try:
            _id = (await moderationColl.find_one({"_id": "config"}))["sbinfoMessages"][category.lower()]
        except KeyError:
            return await ctx.send("Could not find that category")
        msg: discord.Message = await ctx.guild.get_channel(788162727461781504).fetch_message(_id)
        embed = msg.embeds[0]
        if param == "colour":
            try:
                value = int(value, 16)
            except ValueError:
                return await ctx.send("Invalid hex colour")
        setattr(embed, param, value)
        await msg.edit(embed=embed)
        await ctx.send("Done!")
        await ctx.message.delete()


def setup(bot):
    bot.add_cog(Staff(bot, True))
