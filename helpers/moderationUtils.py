import discord
import datetime

MUTED_ROLE = 678911295835078657
GUILD_ID = 667953033929293855
LOG_CHANNEL_ID = 667957285837864960
DELETE_WARNS_AFTER = 1209600

colours = {
    "warn": 0xF7FF00,
    "mute": 0xFF8F00,
    "kick": 0xFF5D00,
    "ban": 0xFF0000
}

async def end_punishment(bot, payload, moderator, reason):
    guild = bot.get_guild(GUILD_ID)
    if payload["type"] == "mute":
        member = guild.get_member(payload["offender_id"])
        await member.remove_roles(guild.get_role(MUTED_ROLE))
    elif payload["type"] == "ban":
        await guild.unban(payload["offender_id"], reason="punishment ended")
    await end_log(bot, payload, moderator=moderator, reason=reason)

def chatEmbed(ctx, payload):
    offender = ctx.bot.get_user(payload["offender_id"])
    embed = discord.Embed(title=payload["type"], colour=colours[payload["type"]], description=payload["reason"] if payload["reason"] else "").set_author(name=offender, icon_url=offender.avatar_url)
    return embed

async def end_log(bot, payload, *, moderator, reason):
    user = bot.get_user(payload["offender_id"])
    embed = discord.Embed(title=f"un{payload['type']}", colour=discord.Colour.green()).set_author(name=user, icon_url=user.avatar_url)
    embed.add_field(name="moderator", value=moderator, inline=False)
    embed.add_field(name="reason", value=reason, inline=False)
    await bot.get_guild(GUILD_ID).get_channel(LOG_CHANNEL_ID).send(embed=embed)

async def log(bot, payload):
    offender = bot.get_user(payload["offender_id"])
    embed = discord.Embed(title=payload["type"], colour=colours[payload["type"]]).set_author(name=offender, icon_url=offender.avatar_url)
    embed.add_field(name="reason", value=payload["reason"], inline=False)
    embed.add_field(name="Moderator", value=f"<@{payload['mod_id']}>", inline=False)
    if "duration" in payload:
        embed.add_field(name="duration", value=payload["duration_string"])
    embed.set_footer(text=f"case ID: {payload['id']}")
    embed.timestamp = datetime.datetime.now()
    await bot.get_guild(GUILD_ID).get_channel(LOG_CHANNEL_ID).send(embed=embed)