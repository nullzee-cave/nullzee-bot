import re
from motor.motor_asyncio import AsyncIOMotorClient
from api_key import userColl
import discord
import json
import datetime
import random
import string
from discord.ext import commands

staff_only = commands.check(lambda ctx: ctx.guild and ctx.guild.id == 667953033929293855 and (685027474522112000 in
                                                                                              (roles := [z.id for z in
                                                                                                         ctx.author.roles]) or
                                                                                              667953757954244628 in roles))

staff_or_trainee = commands.check(lambda ctx: ctx.guild and ctx.guild.id == 667953033929293855 and (685027474522112000 in
                                                                                              (roles := [z.id for z in
                                                                                                         ctx.author.roles]) or
                                                                                              667953757954244628 in roles or
                                                                                              675031583954173986 in roles))


async def get_user(user):
    if not await userColl.find_one({"_id": str(user.id)}):
        await userColl.insert_one(
            {"_id": str(user.id), "experience": 0, "weekly": 0, "level": 1, "last_message": 0, "points": 0,
             "last_points": 0, "embed_colour": "#00FF00", "vc_minutes": 0})
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


def nanoId(length=20):
    return ''.join(
        random.choice(string.ascii_uppercase + string.ascii_lowercase + string.digits) for _ in range(length))


def getFileJson(filename):
    with open(f"{filename}.json") as f:
        return json.load(f)


def saveFileJson(data, filename):
    with open(f"{filename}.json", 'w') as f:
        json.dump(data, f)


class RoleConverter(commands.Converter):
    abbreviations = {"vc lord": 682656964123295792, "godly giveaway donator": 681900556788301843}

    async def convert(self, ctx, argument) -> discord.Role:
        role = None
        try:
            role = await commands.RoleConverter().convert(ctx, argument)
        except commands.RoleNotFound:
            if argument in self.abbreviations:
                role = ctx.guild.get_role(self.abbreviations[argument])
            else:
                role_list_lower = {z.name.lower(): z for z in ctx.guild.roles}
                if argument in role_list_lower:
                    role = role_list_lower[argument]
        finally:
            if role:
                return role
            raise commands.RoleNotFound(argument)


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
    regex = "(\d+)(.)"
    d = {"s": 1, "m": 60, "h": 3600, "d": 86400, "w": 604800}
    match = re.search(regex, _string)
    if not match:
        return None
    else:
        return int(match.group(1)) * d[match.group(2)] if match.group(2) in d else None
