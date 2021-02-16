import discord
import datetime
from api_key import moderationColl

# MUTED_ROLE = 678911295835078657
MUTED_ROLE = 749178299518943343
GUILD_ID = 667953033929293855
LOG_CHANNEL_ID = 667957285837864960
DELETE_WARNS_AFTER = 1209600

PAST_PARTICIPLES = {
    "mute": "Muted",
    "ban": "Banned",
    "warn": "Warned",
    "kick": "Kicked"
}

COLOURS = {
    "warn": 0xF7FF00,
    "mute": 0xFF8F00,
    "kick": 0xFF5D00,
    "ban": 0xFF0000
}

SEVERITY = {
    "warn": 1,
    "mute": 3,
    "kick": 9,
    "ban": 18
}


doc = {}
async def update_config():
    global doc
    doc = await moderationColl.find_one({"_id": "config"})

async def get_config():
    if not doc:
        await update_config()
    return doc


class BannedUser(object):
    def __init__(self, _id):
        self.id = _id

async def warn_punishments(ctx, user):
    warns = [z async for z in moderationColl.find({"offender_id": user.id, "expired": False})]
    config = await get_config()
    score = sum([SEVERITY[z["type"]] for z in warns if z["type"] == "warn" or z["mod_id"] != ctx.bot.user.id])
    punishment = config["punishForWarns"][str(score)] if str(score) in config["punishForWarns"] else None
    if not punishment:
        if int(list(config["punishForWarns"].keys())[-1]) < score:
            await ctx.invoke(ctx.bot.get_command("ban"), user, 31536000, reason="maximum warning limit exceeded")
        return
    ctx.author = ctx.guild.me
    cmd = ctx.bot.get_command(punishment["type"].lower())
    if not cmd: return
    if cmd.name == "kick":
        return await ctx.invoke(cmd, user, reason=f"{score} warns")
    await ctx.invoke(cmd, user, punishment["duration"], reason=f"{score} warns")

async def end_punishment(bot, payload, moderator, reason):
    try:
        guild = bot.get_guild(GUILD_ID)
        if payload["type"] == "mute":
            member = guild.get_member(payload["offender_id"])
            await member.remove_roles(guild.get_role((await get_config())["muteRole"]))
        elif payload["type"] == "ban":
            await guild.unban(BannedUser(payload["offender_id"]), reason="punishment ended")
        await end_log(bot, payload, moderator=moderator, reason=reason)
    except:
        return

def chatEmbed(ctx, payload):
    offender = ctx.bot.get_user(payload["offender_id"])
    embed = discord.Embed(title=f'**{PAST_PARTICIPLES[payload["type"]]}**', colour=COLOURS[payload["type"]], description=payload["reason"] if payload["reason"] else "").set_author(name=offender, icon_url=offender.avatar_url)
    return embed

async def end_log(bot, payload, *, moderator, reason):
    user = bot.get_user(payload["offender_id"])
    embed = discord.Embed(title=f"Un{payload['type']}", colour=discord.Colour.green()).set_author(name=user, icon_url=user.avatar_url)
    embed.add_field(name="Reason", value=reason, inline=False)
    embed.add_field(name="Moderator", value=moderator, inline=False)
    await bot.get_guild(GUILD_ID).get_channel(LOG_CHANNEL_ID).send(embed=embed)

async def log(bot, payload):
    offender = bot.get_user(payload["offender_id"])
    embed = discord.Embed(title=payload["type"].capitalize(), colour=COLOURS[payload["type"]]).set_author(name=offender, icon_url=offender.avatar_url)
    embed.add_field(name="Reason", value=payload["reason"], inline=False)
    embed.add_field(name="Moderator", value=f"<@{payload['mod_id']}>", inline=False)
    if "duration" in payload and payload["duration"]:
        embed.add_field(name="Duration", value=payload["duration_string"])
    embed.set_footer(text=f"Case ID: {payload['id']}")
    embed.timestamp = datetime.datetime.now()
    await bot.get_guild(GUILD_ID).get_channel(LOG_CHANNEL_ID).send(embed=embed)
