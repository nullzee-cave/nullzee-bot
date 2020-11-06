import discord
import datetime

colours = {
    "warn": 0xF7FF00,
    "mute": 0xFF8F00,
    "kick": 0xFF5D00,
    "ban": 0xFF0000
}

async def log(bot, payload):
    offender = bot.get_user(payload["offender_id"])
    embed = discord.Embed(title=payload["type"], colour=colours[payload["type"]]).set_author(name=offender, icon_url=offender.avatar_url)
    embed.add_field(name="reason", value=payload["reason"], inline=False)
    embed.add_field(name="Moderator", value=f"<@{payload['mod_id']}>", inline=False)
    if "duration" in payload:
        embed.add_field(name="duration", value=payload["duration_string"])
    embed.set_footer(text=f"case ID: {payload['id']}")
    embed.timestamp = datetime.datetime.now()
    await bot.get_guild(667953033929293855).get_channel(667957285837864960).send(embed=embed)