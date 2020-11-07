import discord
import datetime
from api_key import moderationColl

# MUTED_ROLE = 678911295835078657
MUTED_ROLE = 749178299518943343
GUILD_ID = 667953033929293855
LOG_CHANNEL_ID = 667957285837864960
DELETE_WARNS_AFTER = 1209600

PAST_PARTICIPLES = {
    "mute": "muted",
    "ban": "banned",
    "warn": "warned",
    "kick": "kicked"
}

colours = {
    "warn": 0xF7FF00,
    "mute": 0xFF8F00,
    "kick": 0xFF5D00,
    "ban": 0xFF0000
}

class BannedUser(object):
    def __init__(self, _id):
        self.id = _id

async def warn_punishments(ctx, user):
    warns = [z async for z in moderationColl.find({"offender_id": user.id, "expired": False})]
    if len(warns) == 3:
        await ctx.invoke(ctx.bot.get_command("mute"), user, "1d", reason="3 warnings within 2 weeks")


async def end_punishment(bot, payload, moderator, reason):
    guild = bot.get_guild(GUILD_ID)
    if payload["type"] == "mute":
        member = guild.get_member(payload["offender_id"])
        await member.remove_roles(guild.get_role(MUTED_ROLE))
    elif payload["type"] == "ban":
        try:
            await guild.unban(BannedUser(payload["offender_id"]), reason="punishment ended")
        except (discord.NotFound, discord.HTTPException):
            return
    await end_log(bot, payload, moderator=moderator, reason=reason)

def chatEmbed(ctx, payload):
    offender = ctx.bot.get_user(payload["offender_id"])
    embed = discord.Embed(title=f'**{PAST_PARTICIPLES[payload["type"]]}**', colour=colours[payload["type"]], description=payload["reason"] if payload["reason"] else "").set_author(name=offender, icon_url=offender.avatar_url)
    return embed

async def end_log(bot, payload, *, moderator, reason):
    user = bot.get_user(payload["offender_id"])
    embed = discord.Embed(title=f"un{payload['type']}", colour=discord.Colour.green()).set_author(name=user if user else "", icon_url=user.avatar_url if user else "")
    embed.add_field(name="moderator", value=moderator, inline=False)
    embed.add_field(name="reason", value=reason, inline=False)
    await bot.get_guild(GUILD_ID).get_channel(LOG_CHANNEL_ID).send(embed=embed)

async def log(bot, payload):
    offender = bot.get_user(payload["offender_id"])
    embed = discord.Embed(title=payload["type"], colour=colours[payload["type"]]).set_author(name=offender, icon_url=offender.avatar_url)
    embed.add_field(name="reason", value=payload["reason"], inline=False)
    embed.add_field(name="Moderator", value=f"<@{payload['mod_id']}>", inline=False)
    if "duration" in payload and payload["duration"]:
        embed.add_field(name="duration", value=payload["duration_string"])
    embed.set_footer(text=f"case ID: {payload['id']}")
    embed.timestamp = datetime.datetime.now()
    await bot.get_guild(GUILD_ID).get_channel(LOG_CHANNEL_ID).send(embed=embed)