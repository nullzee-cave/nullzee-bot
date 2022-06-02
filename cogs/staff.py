import traceback

import discord
import ast
from discord.ext import commands
import json
import datetime

from helpers.events import Emitter
from helpers.utils import string_to_seconds as sts, Embed, TimeConverter, staff_only, RoleConverter, staff_or_trainee, \
    MemberUserConverter
from helpers.constants import Role, Channel, Misc
from helpers import moderation_utils
import asyncio
from api_key import user_coll, moderation_coll, giveaway_coll, DEV_ID
import subprocess
import typing


def insert_returns(body):
    # insert return stmt if the last expression is a expression statement
    if isinstance(body[-1], ast.Expr):
        body[-1] = ast.Return(body[-1].value)
        ast.fix_missing_locations(body[-1])


class Staff(commands.Cog, name="Staff"):
    """All general staff-only commands that don't fit into other categories"""

    def __init__(self, bot, hidden):
        self.hidden = hidden
        self.bot: commands.Bot = bot

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        if guild.id in [Misc.GUILD]:
            return
        embed = discord.Embed(title=f"UNAUTHORISED GUILD JOIN", colour=discord.Colour.red())
        embed.add_field(name="guild info",
                        value=f"ID: {guild.id}\nName: {guild.name}\nMembers: {guild.member_count}", inline=False)
        embed.add_field(name="owner", value=f"{guild.owner} ({guild.owner.id})", inline=False)
        try:
            embed.add_field(name="invite", value=str(await [z for z in guild.channels if
                            isinstance(z, discord.TextChannel) or
                            isinstance(z, discord.VoiceChannel)][0].create_invite()),
                            inline=False)
        except Exception as err:
            print(f"EXCEPTION TRACE PRINT:\n{''.join(traceback.format_exception(type(err), err, err.__traceback__))}")
            pass
        await guild.leave()
        await self.bot.get_user(DEV_ID).send(embed=embed)

    @commands.command(hidden=True)
    @staff_or_trainee
    async def pending(self, ctx, user: discord.Member = None):
        """Check if a user has completed member screening or not"""
        if user is None:
            user = ctx.author
        if user.pending:
            embed = discord.Embed(title="True", description=f"{user.mention} has not completed member screening",
                                  colour=user.colour)
            embed.set_author(name=user, icon_url=user.avatar)
            return await ctx.send(embed=embed)
        elif not user.pending:
            embed = discord.Embed(title="False", description=f"{user.mention} has completed member screening",
                                  colour=user.colour)
            embed.set_author(name=user, icon_url=user.avatar)
            return await ctx.send(embed=embed)
        else:
            return await ctx.send("you've somehow managed to make a binary value not be true or false, congrats")

    @commands.command(hidden=True, aliases=["say"])
    @staff_only
    async def send(self, ctx, channel: typing.Optional[discord.TextChannel] = None, *, message: str):
        """Make the bot send a message"""
        channel = channel if channel else ctx.channel
        if not ctx.author.permissions_in(channel).send_messages:
            raise commands.MissingPermissions(["manage_messages"])
        msg = await channel.send(message)
        if channel.id != ctx.channel.id:
            await ctx.send(msg.jump_url)

    @commands.command(hidden=True)
    @staff_only
    async def reply(self, ctx, message: discord.Message, ping: typing.Optional[bool] = True, *, text: str):
        """Make the bot reply to a message"""
        if not ctx.author.permissions_in(message.channel).send_messages:
            raise commands.MissingPermissions(["manage_messages"])
        msg = await message.reply(content=text, mention_author=ping)
        if message.channel.id != ctx.channel.id:
            await ctx.send(msg.jump_url)

    @commands.command(hidden=True)
    @staff_or_trainee
    async def qotd(self, ctx):
        """Mark today's qotd as done"""
        with open("config.json") as f:
            config = json.load(f)
        config["qotd"] = (datetime.datetime.now() - datetime.datetime.utcfromtimestamp(0)).days
        with open("config.json", "w") as f:
            json.dump(config, f)
        await ctx.send("Last QOTD time set to now")

    @commands.command(hidden=True)
    @staff_or_trainee
    async def slowmode(self, ctx, _time="off"):
        """Change the channel's slowmode"""
        if _time.lower() == "off":
            await ctx.channel.edit(slowmode_delay=0)
            return await ctx.send(f"Slowmode has been removed from {ctx.channel.mention} by {ctx.author.mention}")
        else:
            timer = sts(_time)
            if not timer:
                return await ctx.send("invalid slowmode time")
            else:
                await ctx.channel.edit(slowmode_delay=timer)
                return await ctx.send(f"slowmode has been set to `{_time}` by {ctx.author.mention}")

    @commands.command(name="role", hidden=True)
    @staff_or_trainee
    async def give_role(self, ctx, user: discord.Member, *, role: RoleConverter):
        """Give someone a role"""
        if role.permissions.manage_messages or role.permissions.administrator \
                or role.permissions.manage_roles or role.id in [Role.MUTED, Role.STAFF_ROLES]:
            return await ctx.send("You are not allowed to give that role")
        try:
            await user.add_roles(role, reason=f"Given by {ctx.author}")
            embed = discord.Embed(title="Role added :scroll:",
                                  description=f":white_check_mark: Gave {role.mention} to {user.mention}",
                                  colour=0xfb00fd)
            await ctx.send(embed=embed)
            await ctx.message.delete()
        except discord.Forbidden:
            return await ctx.send("I do not have permission to give that role to that user")

    @commands.command(name="removerole", hidden=True)
    @staff_or_trainee
    async def remove_role(self, ctx, user: discord.Member, *, role: RoleConverter):
        """Remove a role from someone"""
        if role.permissions.manage_messages or role.permissions.administrator \
                or role.permissions.manage_roles or role.id in [Role.MUTED, Role.STAFF_ROLES]:
            return await ctx.send("You are not allowed to remove that role")
        try:
            await user.remove_roles(role, reason=f"Removed by {ctx.author}")
            embed = discord.Embed(title="Role removed :scroll:",
                                  description=f":white_check_mark: Removed {role.mention} from {user.mention}",
                                  color=0xfb00fd)
            await ctx.send(embed=embed)
            await ctx.message.delete()
        except discord.Forbidden:
            return await ctx.send("I do not have permission to remove that role from that user")

    @commands.command(aliases=["star"], hidden=True)
    @staff_or_trainee
    async def starboard(self, ctx: commands.Context, msg: discord.Message, *, title: str = ""):
        """Add a message to the starboard"""
        embed = Embed(msg.author, title=f"{title} | #{ctx.channel.name}", description=msg.content, url=msg.jump_url)
        embed.set_footer(text=f"Starred by {ctx.author}").auto_author().timestamp_now()
        await embed.user_colour()
        if msg.attachments:
            embed.set_image(url=msg.attachments[0].url)
        star_message = await ctx.guild.get_channel(Channel.STARBOARD).send(embed=embed)
        embed = Embed(ctx.author, title="Added to starboard!", url=star_message.jump_url)
        await embed.user_colour()
        await ctx.send(embed=embed)
        ctx.author = msg.author
        await Emitter().emit("pinned_starred", ctx)

    @commands.command(aliases=["clear"], hidden=True)
    @staff_or_trainee
    async def purge(self, ctx, user: typing.Optional[MemberUserConverter] = None, limit: int = 0):
        """Purge messages in a channel"""
        if limit <= 0:
            raise commands.UserInputError

        if user is None:
            def check(m):
                return not m.pinned

            await ctx.channel.purge(limit=limit + 1, check=check)

            await asyncio.sleep(1)
            chat_embed = discord.Embed(description=f"Cleared {limit} messages", color=0xfb00fd)
            chat_embed.set_author(name=ctx.author, icon_url=ctx.author.avatar)
            await ctx.send(embed=chat_embed)
            log_embed = discord.Embed(title="Purge", description=f"{limit} messages cleared from {ctx.channel.mention}")
            log_embed.set_author(name=ctx.author, icon_url=ctx.author.avatar)
            log_channel = ctx.guild.get_channel(Channel.MOD_LOGS)
            await log_channel.send(embed=log_embed)
        else:
            await ctx.message.delete()
            to_delete = []
            async for message in ctx.channel.history():
                if len(to_delete) >= limit:
                    break
                if message.author.id == user.id:
                    to_delete.append(message)
            await ctx.channel.delete_messages(to_delete)

            await asyncio.sleep(1)
            chat_embed = discord.Embed(description=f"Cleared {limit} messages from {user.mention}", color=0xfb00fd)
            chat_embed.set_author(name=ctx.author, icon_url=ctx.author.avatar)
            await ctx.send(embed=chat_embed)
            log_embed = discord.Embed(title="Purge",
                                      description=f"{limit} messages from {user.mention} "
                                                  f"cleared from {ctx.channel.mention}")
            log_embed.set_author(name=ctx.author, icon_url=ctx.author.avatar)
            log_channel = ctx.guild.get_channel(Channel.MOD_LOGS)
            await log_channel.send(embed=log_embed)


    @commands.command(hidden=True, name="eval", aliases=["eval_fn", "-e"])
    async def eval_fn(self, ctx, *, cmd):
        """Evaluates input.
        Input is interpreted as newline seperated statements.
        If the last statement is an expression, that is the return value.
        Usable globals:
        - `bot`: the bot instance
        - `discord`: the discord module
        - `commands`: the discord.ext.commands module
        - `ctx`: the invocation context
        - `__import__`: the builtin `__import__` function
        Such that `>eval 1 + 1` gives `2` as the result.
        The following invocation will cause the bot to send the text '9'
        to the channel of invocation and return '3' as the result of evaluating
        >eval ```
        a = 1 + 2
        b = a * 2
        await ctx.send(a + b)
        a
        ```
        """
        owners = [564798709045526528, 540939418933133312]
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
                "bot": ctx.bot,
                "discord": discord,
                "commands": commands,
                "ctx": ctx,
                "user_coll": user_coll,
                "moderation_coll": moderation_coll,
                "giveaway_coll": giveaway_coll,
                "__import__": __import__
            }

            try:
                exec(compile(parsed, filename="<ast>", mode="exec"), env)
                result = (await eval(f"{fn_name}()", env))
                await ctx.send(f"```py\n{result}\n```")
            except Exception as e:
                await ctx.send(f"An exception occurred:```py\n{e}\n```")

    @commands.command(hidden=True, aliases=['-he'])
    async def host_eval(self, ctx, *, args):
        """Eval but straight into the host machine"""
        if ctx.author.id in [564798709045526528, 540939418933133312]:
            await ctx.send(f"```\n{subprocess.check_output(args.split(' ')).decode('utf-8')[:1900]}\n```")

    @commands.command(name="modhelp", hidden=True)
    @staff_or_trainee
    async def moderation_help(self, ctx):
        """View the help menu for all moderation commands"""
        bot: commands.Bot = ctx.bot
        mod_cogs = [bot.get_cog(z) for z in bot.cogs]
        mod_cogs = filter(lambda x: x.hidden, mod_cogs)
        embed = discord.Embed(title="Moderation Help!", colour=discord.Colour.gold())
        string = ""
        for cog in mod_cogs:
            cog_string = ""
            for cmd in cog.get_commands():
                cog_string += f"\n`{ctx.PREFIX}{cmd.name}`"
            string += f"\n**{cog.qualified_name}:**{cog_string}"
        embed.description = string
        await ctx.send(embed=embed)

    @commands.command(name="messagejson", hidden=True)
    @staff_only
    async def message_json(self, ctx: commands.Context, message: discord.Message):
        """Returns the given message as a JSON file"""
        json_object = {"content": message.content, "embeds": [z.to_dict() for z in message.embeds]}
        json_string = json.dumps(json_object)
        if len(json_string) <= 2000:
            return await ctx.send(f"```json\n{json_string}\n```")
        else:
            with open("message.json", "w") as f:
                json.dump(json_object, f, indent=4)
            await ctx.send(file=discord.File("message.json"))

    # TODO: Rewrite all of the remaining code in this cog
    # Honestly it's a lost cause as it is

    @commands.group(hidden=True, invoke_without_command=True)
    @staff_only
    async def blacklist(self, ctx):
        """The blacklist commands"""
        pass

    @blacklist.command(hidden=True, name="add")
    @staff_only
    async def blist_add(self, ctx, member: discord.Member, command: str):
        """Add a user to the blacklist for a specific command"""
        command = command.replace(ctx.PREFIX, '')
        await user_coll.update_one({"_id": str(member.id)}, {"$addToSet": {"command_blacklist": command}})
        await ctx.send(f"blacklisted `{member}` from using `{ctx.PREFIX}{command}`")

    @blacklist.command(hidden=True, name="remove")
    @staff_only
    async def blist_remove(self, ctx, member: discord.Member, command: str):
        """Remove a user from the blacklist for a specific command"""
        command = command.replace(ctx.PREFIX, '')
        await user_coll.update_one({"_id": str(member.id)}, {"$pull": {"command_blacklist": command}})
        await ctx.send(f"unblacklisted `{member}` from using `{ctx.PREFIX}{command}`")

    @commands.group(hidden=True, aliases=["-c"])
    @staff_or_trainee
    async def config(self, ctx):
        """Edit the config"""
        if not ctx.invoked_subcommand:
            await ctx.send(
                "\n".join([f"- {z.name}{'*' if isinstance(z, commands.Group) else ''}" for z in self.config.commands]))
        else:
            await ctx.send("Successfully updated configuration")
            await moderation_utils.update_config()

    @config.command(hidden=True)
    async def mutedRole(self, ctx, *, role: discord.Role):
        await moderation_coll.update_one({"_id": "config"}, {"$set": {"mutedRole": role.id}})

    @config.command(hidden=True)
    async def deleteWarnsAfter(self, ctx, _time: TimeConverter):
        await moderation_coll.update_one({"_id": "config"}, {"$set": {"deleteWarnsAfter": _time}})

    @config.group(hidden=True, invoke_without_command=True)
    async def punishForWarns(self, ctx):
        await ctx.send("\n".join(
            [f"- {z.name}{'*' if isinstance(z, commands.Group) else ''}" for z in self.punishForWarns.commands]))

    @punishForWarns.command(hidden=True, name="add")
    async def p_add(self, ctx, warns: int, duration: TimeConverter, _type="mute"):
        await moderation_coll.update_one({"_id": "config"}, {
            "$set": {"punishForWarns.{}".format(warns): {"type": _type, "duration": duration}}})

    @punishForWarns.command(hidden=True, name="remove")
    async def p_remove(self, ctx, warns: int):
        await moderation_coll.update_one({"_id": "config"}, {"$unset": {"punishForWarns.{}".format(warns): ""}})

    @config.group(hidden=True, invoke_without_command=True)
    async def automod(self, ctx):
        await ctx.send(
            "\n".join([f"- {z.name}{'*' if isinstance(z, commands.Group) else ''}" for z in self.automod.commands]))

    @automod.group(hidden=True, invoke_without_command=True)
    async def mentions(self, ctx):
        await ctx.send(
            "\n".join([f"- {z.name}{'*' if isinstance(z, commands.Group) else ''}" for z in self.mentions.commands]))

    @mentions.command(hidden=True, name="punishment")
    async def m_punishment(self, ctx, action: str = "delete"):
        await moderation_coll.update_one({"_id": "config"},
                                         {"$set": {"mentions.action": action if action == "warn" else "delete"}})

    @mentions.command(hidden=True)
    async def value(self, ctx, val: int):
        await moderation_coll.update_one({"_id": "config"}, {"$set": {"mentions.val": val}})

    @mentions.command(hidden=True, name="allowChannel")
    async def m_allowChannel(self, ctx, channel: discord.TextChannel):
        await moderation_coll.update_one({"_id": "config"}, {"$push": {"mentions.allowed_channels": channel.id}})

    @mentions.command(hidden=True, name="disallowChannel")
    async def m_disallowChannel(self, ctx, channel: discord.TextChannel):
        await moderation_coll.update_one({"_id": "config"}, {"$pull": {"mentions.allowed_channels": channel.id}})

    @automod.group(hidden=True, invoke_without_command=True)
    async def invites(self, ctx):
        await ctx.send(
            "\n".join([f"- {z.name}{'*' if isinstance(z, commands.Group) else ''}" for z in self.invites.commands]))

    @invites.command(hidden=True, name="punishment")
    async def i_punishment(self, ctx, action: str = "delete"):
        await moderation_coll.update_one({"_id": "config"},
                                         {"$set": {"invites.action": action if action == "warn" else "delete"}})

    @invites.command(hidden=True, name="allowChannel")
    async def i_allowChannel(self, ctx, channel: discord.TextChannel):
        await moderation_coll.update_one({"_id": "config"}, {"$push": {"invites.allowed_channels": channel.id}})

    @invites.command(hidden=True, name="disallowChannel")
    async def i_disallowChannel(self, ctx, channel: discord.TextChannel):
        await moderation_coll.update_one({"_id": "config"}, {"$pull": {"invites.allowed_channels": channel.id}})

    @automod.group(hidden=True, invoke_without_command=True, case_insensitive=True)
    async def badWords(self, ctx):
        await ctx.send(
            "\n".join([f"- {z.name}{'*' if isinstance(z, commands.Group) else ''}" for z in self.badWords.commands]))

    @badWords.command(hidden=True, name="add")
    async def b_add(self, ctx, word: str, action: str = "delete"):
        await moderation_coll.update_one({"_id": "config"}, {"$set": {"badWords.{}".format(word.lower()): action}})

    @badWords.command(hidden=True, name="remove")
    async def b_remove(self, ctx, word: str):
        await moderation_coll.update_one({"_id": "config"}, {"$unset": {"badWords.{}".format(word.lower()): ""}})

    @automod.group(hidden=True, invoke_without_command=True, case_insensitive=True)
    async def scamLinks(self, ctx):
        await ctx.send(
            "\n".join([f"- {z.name}{'*' if isinstance(z, commands.Group) else ''}" for z in self.scamLinks.commands]))

    @scamLinks.command(hidden=True, name="addLink")
    async def s_add(self, ctx, link: str, action: str = "ban"):
        split_link = link.split("/")
        if len(split_link) < 3 or "." not in split_link[2]:
            return await ctx.send("Invalid link format")
        formatted_link = f"https?;//{split_link[2].replace('.', ',')}"
        await ctx.send(f"Added `http(s)://{split_link[2]}` to automod")
        await moderation_coll.update_one({"_id": "config"},
                                         {"$set": {"scamLinks.{}".format(formatted_link.lower()): action}})

    @scamLinks.command(hidden=True, name="removeLink")
    async def s_remove(self, ctx, link: str):
        split_link = link.split("/")
        if len(split_link) < 3 or "." not in split_link[2]:
            return await ctx.send("Invalid link format")
        formatted_link = f"https?;//{split_link[2].replace('.', ',')}"
        await ctx.send(f"Removed `http(s)://{split_link[2]}` to automod")
        await moderation_coll.update_one({"_id": "config"},
                                         {"$unset": {"scamLinks.{}".format(formatted_link.lower()): ""}})

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

    @commands.command(name="SkyblockAnnouncement", aliases=["sbannouncement"])
    @commands.has_any_role(Role.STAFF, Role.SB_ADVISER)
    @commands.guild_only()
    async def skyblock_announcement(self, ctx: commands.Context, title: str, *, description: str):
        f"""Ping Skyblock Ping with a message in <#{Channel.SB_RES}>"""
        await ctx.guild.get_channel(Channel.SB_RES).send(f"<@&{Role.SKYBLOCK_PING}>", embed=discord.Embed(title=title, description=description, colour=0x00ff00))

    @commands.group(invoke_without_command=True)
    async def sbinfo(self, ctx, category: str):
        """Skyblock Resources commands"""
        try:
            _id = (await moderation_coll.find_one({"_id": "config"}))["sbinfoMessages"][category.lower()]
        except KeyError:
            return await ctx.send("Could not find that category")
        url = f"https://discord.com/channels/{Misc.GUILD}/{Channel.SB_RES}/{_id}"
        await ctx.send(
            embed=discord.Embed(title=category, description=f"Click [here]({url}) to view info about {category}",
                                colour=0x00ff00, url=url))

    @sbinfo.command()
    @commands.guild_only()
    @commands.has_any_role(Role.SB_ADVISER, Role.STAFF)
    async def newCategory(self, ctx: commands.Context, name: str, *, description: str = None):
        f"""Create a new category in <#{Channel.SB_RES}>"""
        msg: discord.Message = await ctx.guild.get_channel(Channel.SB_RES).send(
            embed=discord.Embed(title=name, description=description, colour=0x00FF00))
        await moderation_coll.update_one({"_id": "config"}, {"$set": {f"sbinfoMessages.{name.lower()}": msg.id}})
        await ctx.send("Successfully created category")
        await ctx.message.delete()

    @sbinfo.command(name="add")
    @commands.guild_only()
    async def sbi_add(self, ctx: commands.Context, category: str, name: str, *, description: str):
        f"""Add a field to a category in <#{Channel.SB_RES}"""
        try:
            _id = (await moderation_coll.find_one({"_id": "config"}))["sbinfoMessages"][category.lower()]
        except KeyError:
            return await ctx.send("Could not find that category")
        msg: discord.Message = await ctx.guild.get_channel(Channel.SB_RES).fetch_message(_id)
        await msg.edit(embed=msg.embeds[0].add_field(name=name, value=description, inline=False))
        await ctx.send("Done!")
        await ctx.message.delete()

    @sbinfo.command(name="edit")
    @commands.guild_only()
    @commands.has_any_role(Role.SB_ADVISER, Role.STAFF)
    async def sbi_edit(self, ctx, category: str, param: str, *, value):
        f"""Edit a category in <#{Channel.SB_RES}"""
        try:
            _id = (await moderation_coll.find_one({"_id": "config"}))["sbinfoMessages"][category.lower()]
        except KeyError:
            return await ctx.send("Could not find that category")
        msg: discord.Message = await ctx.guild.get_channel(Channel.SB_RES).fetch_message(_id)
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


async def setup(bot):
    await bot.add_cog(Staff(bot, True))
