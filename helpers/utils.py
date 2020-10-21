import re
from motor.motor_asyncio import AsyncIOMotorClient
from api_key import userColl
import discord
import json

async def get_user(user):
    if not await userColl.find_one({"_id": str(user.id)}):
        await userColl.insert_one(
            {"_id": str(user.id), "experience": 0, "weekly": 0, "level": 1, "last_message": 0, "points": 0,
             "last_points": 0, "embed_colour": "#00FF00"})
    return await userColl.find_one({"_id": str(user.id)})


def getFileJson(filename):
    with open(f"{filename}.json") as f:
        return json.load(f)
def saveFileJson(data, filename):
    with open(f"{filename}.json", 'w') as f:
        json.dump(data, f)

class Embed(discord.Embed):
    def __init__(self, user: discord.User, **kwargs):
        self.user = user
        super().__init__(**kwargs)

    async def user_colour(self):
        try:
            self.color = discord.Colour((await get_user(self.user))["embed_colour"])
        except:
            self.color = 0x00FF00
        return self

def min_level(level: int):
    async def predicate(ctx):
        if 706285767898431500 in (
        roles := [z.id for z in ctx.author.roles]) or 668724083718094869 in roles or 668736363297898506 in roles:
            return True
        user = await userColl.find_one({"_id": str(ctx.author.id)})
        if not user:
            return False
        if user["level"] < level:
            return False
        return True

    return predicate


def stringToSeconds(string):
    regex = "(\d+)(.)"
    d = {"s": 1, "m": 60, "h": 3600, "d": 86400}
    match = re.search(regex, string)
    if not match:
        return None
    else:
        return int(match.group(1)) * d[match.group(2)]
