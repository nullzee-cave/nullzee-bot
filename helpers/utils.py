import asyncio
import re
import typing

import aiohttp

from api_key import user_coll
import discord
import json
import datetime
import random
import string
import collections
from discord.ext import commands

from helpers.constants import Role, Misc


def staff_check(ctx):
    if not ctx.guild or ctx.guild.id != Misc.GUILD:
        return False
    roles = role_ids(ctx.author.roles)
    return list_one(roles, Role.STAFF, Role.ADMIN)


def event_hoster_staff_check(ctx):
    if not ctx.guild or ctx.guild.id != Misc.GUILD:
        return False
    roles = role_ids(ctx.author.roles)
    return list_one(roles, Role.EVENT_HOSTER, Role.STAFF, Role.ADMIN)


staff_only = commands.check(staff_check)

staff_or_trainee = commands.check(
    lambda ctx: ctx.guild and ctx.guild.id == Misc.GUILD and (
            Role.ADMIN in (roles := [z.id for z in ctx.author.roles]) or
            Role.STAFF in roles or Role.TRAINEE in roles))

event_hoster_or_staff = commands.check(event_hoster_staff_check)


class MemberUserConverter(commands.Converter):
    async def convert(self, ctx, argument) -> typing.Union[discord.Member, discord.User]:
        try:
            return await commands.MemberConverter().convert(ctx, argument)
        except commands.MemberNotFound:
            try:
                return await commands.UserConverter().convert(ctx, argument)
            except commands.UserNotFound:
                raise commands.UserInputError


class DeltaTemplate(string.Template):
    delimiter = "%"


def strfdelta(tdelta, fmt):
    d = {"Y": tdelta.days // 365, "D": int(tdelta.days) % 365}
    d["H"], rem = divmod(tdelta.seconds, 3600)
    d["M"], d["S"] = divmod(rem, 60)
    t = DeltaTemplate(fmt)
    return t.substitute(**d)


async def get_user(user):
    try:
        await user_coll.insert_one({
            "_id": str(user.id),
            # levelling data
            "experience": 0,
            "weekly": 0,
            "level": 1,
            "last_message": 0,
            # points data
            "points": 0,
            "last_points": 0,
            "embed_colour": "#00FF00",
            # achievement data
            "achievements": {},
            "achievement_inventory": {
                "backgrounds": ["default"],
                "box_borders": ["default"]},
            "achievement_points": 0,
            "background_image": "default",
            "box_border": "default",
            # misc data
            "vc_minutes": 0,
        })
    finally:
        return await user_coll.find_one({"_id": str(user.id)})


def leaderboard_pages(bot, guild: discord.Guild, users, *, key="level", prefix="", suffix="",
                      title="Nullzee's cave leaderboard", field_name="Gain XP by chatting"):
    entries = []
    lb_pos = 1
    for i, user in enumerate(users):
        if not (member := guild.get_member(int(user["_id"]))):
            continue
        entries.append(f"**{lb_pos}: {member}** - {prefix}{user[key]:,}{suffix}\n")
        lb_pos += 1
    embeds = [discord.Embed(colour=0x00FF00).set_author(name=title, icon_url=guild.icon_url)]
    values = [""]
    embed_index = 0
    for i, entry in enumerate(entries):
        values[embed_index] += entry
        if not ((i + 1) % 15) and i != 0:
            embeds.append(discord.Embed(colour=0x00FF00).set_author(name=title, icon_url=guild.icon_url))
            embed_index += 1
            values.append("")
    embeds = embeds[:16]
    for i, embed in enumerate(embeds):
        embed.set_footer(text=f"page {i + 1} of {len(embeds)}")
        embed.add_field(name=field_name, value=values[i], inline=False)
    return embeds


def deep_update_dict(d, u):
    for k, v in u.items():
        if isinstance(v, collections.abc.Mapping):
            d[k] = deep_update_dict(d.get(k, {}), v)
        else:
            d[k] = v
    return d


def nano_id(length=20):
    return "".join(
        random.choice(string.ascii_uppercase + string.ascii_lowercase + string.digits) for _ in range(length))


def get_file_json(filename="config"):
    with open(f"{filename}.json") as f:
        return json.load(f)


def save_file_json(data, filename="config"):
    with open(f"{filename}.json", "w") as f:
        json.dump(data, f)


class MessageOrReplyConverter(commands.Converter):

    async def convert(self, ctx: commands.Context, argument: str):
        message: discord.Message = None
        try:
            message = await commands.MessageConverter().convert(ctx, argument)
        except commands.MessageNotFound:
            message = ctx.message.reference
            message = message.cached_message if message else message
        if message is None:
            raise commands.MessageNotFound(argument)
        return message


class GiveawayError(Exception):
    """
    Exception raised for errors with giveaways
    Currently used for giveaway creation timeout and cancellation
    """

    def __init__(self, description="Please report this to Septikai#1676"):
        self.description = description
        self.embed = discord.Embed(description=description, colour=0xFF0000)

    async def send_error(self, ctx):
        await ctx.send(embed=self.embed)


class HelpError(Exception):
    """Exception raised for errors with the help command"""

    def __init__(self, description="Please report this to Septikai#1676"):
        self.description = description
        self.embed = discord.Embed(title="Error!", description=description, colour=0xFF0000)

    async def send_error(self, ctx):
        await ctx.send(embed=self.embed)


class HelpConverter(commands.Converter):

    async def convert(self, ctx, argument) -> typing.Union[commands.Command, commands.Cog]:
        argument = argument.replace(" ", "").replace("_", "")
        ctx.guild = ctx.bot.get_guild(Misc.GUILD)
        ctx.author = ctx.guild.get_member(ctx.author.id)
        for cog in [ctx.bot.get_cog(z) for z in ctx.bot.COGS]:
            if argument.lower() == cog.qualified_name.lower().replace(" ", "").replace("_", ""):
                if (cog.hidden and not staff_check(ctx)) or cog.get_commands() == []:
                    break
                return cog
            for command in cog.get_commands():
                if argument.lower() == command.name.lower().replace(" ", "").replace("_", ""):
                    if command.hidden and not staff_check(ctx):
                        break
                    return command
        raise HelpError("Command/Cog not found")


class RoleConverter(commands.Converter):
    abbreviations = {"vc lord": Role.VC_LORD, "godly giveaway donator": Role.GODLY_GIVEAWAY_DONOR}

    async def convert(self, ctx: commands.Context, argument: str) -> discord.Role:
        role = None
        try:
            role = await commands.RoleConverter().convert(ctx, argument)
        except commands.RoleNotFound:
            if argument.lower() in self.abbreviations:
                role = ctx.guild.get_role(self.abbreviations[argument.lower()])
            else:
                role_list_lower = {z.name.lower(): z for z in ctx.guild.roles}
                if argument.lower() in role_list_lower:
                    role = role_list_lower[argument.lower()]
                else:
                    candidates = []
                    for name in role_list_lower:
                        if argument.lower() in name:
                            candidates.append(role_list_lower[name])
                    if len(candidates) == 1:
                        role = candidates[0]
                    elif len(candidates) > 1:
                        decision_msg = await ctx.send(
                            embed=discord.Embed(title="Which role?",
                                                description="\n".join([f"{i + 1} : {z.mention}" for i, z in
                                                                       enumerate(candidates)]),
                                                colour=discord.Colour.green()))
                        try:
                            res = await ctx.bot.wait_for("message", check=lambda
                                  msg: msg.author.id == ctx.author.id and msg.channel.id == ctx.channel.id, timeout=60)
                            number = int(res.content)
                            role = candidates[number - 1]
                            await decision_msg.delete()
                            await res.delete()
                        except asyncio.TimeoutError:
                            await ctx.send("Timed out")
                        except (ValueError, TypeError, IndexError):
                            await ctx.send("Invalid index")
        finally:
            if role:
                return role
            raise commands.RoleNotFound(argument)


def role_ids(roles):
    return [z.id for z in roles]


def list_one(_list, *items):
    for item in items:
        if item in _list:
            return True
    return False


def list_every(_list, *items):
    for item in items:
        if item not in _list:
            return False
    return True


class ShallowContext:
    def __init__(self):
        self.channel = None
        self.author = None
        self.guild = None
        self.__send_channel = None

    @classmethod
    async def create(cls, member: discord.Member):
        self = cls()
        self.channel = None
        self.__send_channel = (member.dm_channel or await member.create_dm())
        self.author = member
        self.guild = member.guild
        return self

    async def send(self, *args, **kwargs):
        return await self.__send_channel.send(*args, **kwargs)


class ItemNotFound(commands.BadArgument):
    def __init__(self, msg):
        self.msg = msg

    def embed(self):
        return discord.Embed(title=":x: Item not found :x:", description=self.msg, colour=0xff0000)


def json_meta_converter(meta):
    class JsonMetaConverter(commands.Converter):
        async def convert(self, ctx, argument):
            if argument.lower() in meta.get():
                return argument.lower()
            for bg in meta.get():
                if argument.lower() in meta.get()[bg].aliases:
                    return bg
            raise ItemNotFound("Check your spelling and capitalisation")

    return JsonMetaConverter


def json_meta(filepath, defaults):
    class JsonMeta:

        __filepath = filepath
        __defaults = defaults
        __instance = None

        @classmethod
        def get(cls):
            if not cls.__instance:
                with open(f"{cls.__filepath}.json") as f:
                    cls.__instance = cls(json.load(f))
            return cls.__instance

        def __init__(self, raw):
            self.raw = raw

        def __iter__(self):
            yield from self.raw

        def __getitem__(self, item):
            if item in self.raw and (self.raw[item] or isinstance(self.raw[item], dict)):
                return self.__class__(self.raw[item]) if isinstance(self.raw[item], dict) else self.raw[item]
            return self.__defaults[item] if item in self.__defaults else None

        def __getattr__(self, item):
            if item in self.raw and self.raw[item]:
                return self.__class__(self.raw[item]) if isinstance(self.raw[item], dict) else self.raw[item]
            return self.__defaults[item] if item in self.__defaults else None

        def __contains__(self, item):
            return item in self.raw

    return JsonMeta


class Embed(discord.Embed):
    def __init__(self, user: discord.User, **kwargs):
        self.user = user
        super().__init__(**kwargs)

    async def user_colour(self):
        try:
            self.color = discord.Colour(int((await get_user(self.user))["embed_colour"], base=16))
        except:
            self.color = 0x00FF00
        return self

    def auto_author(self):
        self.set_author(name=self.user.__str__(), icon_url=self.user.avatar_url)
        return self

    def timestamp_now(self):
        self.timestamp = datetime.datetime.now()
        return self


def min_level(level: int):
    async def predicate(ctx):
        if Role.RETIRED_SUPPORTER in (
                roles := [z.id for z in ctx.author.roles]) or Role.BOOSTER in roles or Role.TWITCH_SUB in roles:
            return True
        user = await user_coll.find_one({"_id": str(ctx.author.id)})
        if not user:
            return False
        if user["level"] < level:
            return False
        return True

    return predicate


class TimeConverter(commands.Converter):
    async def convert(self, ctx, argument):
        if isinstance(argument, int):
            return argument
        _time = string_to_seconds(argument)
        if _time:
            return _time
        else:
            raise commands.UserInputError


def string_to_seconds(_string):
    _time = 0
    times = {
        "w": 604800,
        "d": 86400,
        "h": 3600,
        "m": 60,
        "s": 1,
    }
    regex = r" ?(?P<time>(?P<number>\d+) ?(?P<period>w|d|h|m|s)) ?"
    _string = _string.lower()
    match = re.match(regex, _string)
    if match is None:
        return None
    while match:
        _time += int(match.group("number")) * times[match.group("period")]
        _string = _string[len(match.group("time")):]
        match = re.match(regex, _string)
    return _time


def level_from_table(count, table) -> int:
    current_level = table[0]
    for level in table:
        if count < level:
            break
        current_level = level
    return current_level


async def fetch_json_api(url: str) -> dict:
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as res:
            return await res.json()


def clean_message_content(message: str) -> str:
    return re.sub(r"[*_\\|`]*", "", message)


def remove_emojis(message: str) -> str:
    return re.sub(r"<a?:\w+:(\d+)>", "\1", message)
