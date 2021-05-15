import abc
import re
import typing

import pymongo
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import DuplicateKeyError

from api_key import userColl
import discord
import json
import datetime
import random
import string
import collections
from discord.ext import commands

from helpers.constants import Role
from helpers.events import Emitter


def staff_check(ctx):
    if not ctx.guild or ctx.guild.id != 667953033929293855:
        return False
    roles = role_ids(ctx.author.roles)
    return list_one(roles, Role.STAFF, Role.ADMIN)


staff_only = commands.check(staff_check)

staff_or_trainee = commands.check(
    lambda ctx: ctx.guild and ctx.guild.id == 667953033929293855 and (685027474522112000 in
                                                                      (roles := [z.id for z in
                                                                                 ctx.author.roles]) or
                                                                      667953757954244628 in roles or
                                                                      675031583954173986 in roles))

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
    d = {"Y": tdelta.days//365}
    d["D"] = int(tdelta.days) % 365
    d["H"], rem = divmod(tdelta.seconds, 3600)
    d["M"], d["S"] = divmod(rem, 60)
    t = DeltaTemplate(fmt)
    return t.substitute(**d)


async def get_user(user):
    try:
        await userColl.insert_one({
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
        return await userColl.find_one({"_id": str(user.id)})


def leaderboard_pages(bot, guild: discord.Guild, users, *, key="level", prefix="", suffix="",
                      title="Nullzee's cave leaderboard",
                      field_name="Gain XP by chatting"):
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
        embed.set_footer(text=f"page {i + 1} of {len(embeds)}").add_field(name=field_name, value=values[i],
                                                                          inline=False)
    return embeds


def deep_update_dict(d, u):
    for k, v in u.items():
        if isinstance(v, collections.abc.Mapping):
            d[k] = deep_update_dict(d.get(k, {}), v)
        else:
            d[k] = v
    return d


def nanoId(length=20):
    return ''.join(
        random.choice(string.ascii_uppercase + string.ascii_lowercase + string.digits) for _ in range(length))


def getFileJson(filename="config"):
    with open(f"{filename}.json") as f:
        return json.load(f)


def saveFileJson(data, filename="config"):
    with open(f"{filename}.json", 'w') as f:
        json.dump(data, f)


class RoleConverter(commands.Converter):
    abbreviations = {"vc lord": 682656964123295792, "godly giveaway donator": 681900556788301843}

    async def convert(self, ctx, argument) -> discord.Role:
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


def jsonMetaConverter(meta):
    class JsonMetaConverter(commands.Converter):
        async def convert(self, ctx, argument):
            if argument.lower() in meta.get():
                return argument.lower()
            for bg in meta.get():
                if argument.lower() in meta.get()[bg].aliases:
                    return bg
            raise ItemNotFound("Check your spelling and capitalisation")

    return JsonMetaConverter


def jsonMeta(filepath, defaults):
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
        if 706285767898431500 in (
                roles := [z.id for z in
                          ctx.author.roles]) or 668724083718094869 in roles or 668736363297898506 in roles:
            return True
        user = await userColl.find_one({"_id": str(ctx.author.id)})
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
        _time = stringToSeconds(argument)
        if _time:
            return _time
        else:
            raise commands.UserInputError


def stringToSeconds(_string):
    _time = 0
    times = {
        "d": 86400,
        "h": 3600,
        "m": 60,
        "s": 1,
    }
    regex = r" ?(?P<time>(?P<number>\d+) ?(?P<period>d|h|m|s)) ?"
    _string = _string.lower()
    match = re.match(regex, _string)
    if match is None:
        return None
    while match:
        _time += int(match.group('number')) * times[match.group('period')]
        _string = _string[len(match.group('time')):]
        match = re.match(regex, _string)
    return _time
