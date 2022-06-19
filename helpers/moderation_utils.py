import re
from typing import Union

import discord
from discord.ext import commands
import datetime

from helpers.utils import get_file_json, Embed
from helpers.constants import Channel, Misc

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
    "kick": 6,
    "ban": 9,
}

doc = {}

lockdown_data = {}


async def update_config(bot):
    global doc
    doc = await bot.moderation_coll.find_one({"_id": "config"})


async def get_config(bot):
    if not doc:
        await update_config(bot)
    return doc


class BannedUser(object):
    def __init__(self, _id):
        self.id = _id


async def automod_name(bot, user: discord.Member):
    config = await get_config(bot)
    for word in config["badWords"]:
        if (not user.guild_permissions.manage_messages) and (re.findall(word, user.display_name, flags=re.IGNORECASE) or
                                                             re.findall(word, user.name, flags=re.IGNORECASE)):
            action = "banned" if config["badWords"][word] == "ban" else "kicked"
            try:
                await user.send(f"You were {action} from Nullzee's cave for having an inappropriate name")
            except discord.Forbidden:
                pass
            if action == "banned":
                return await user.ban(reason="Inappropriate name")
            await user.kick(reason="Inappropriate name")


async def send_report(ctx: Union[commands.Context, discord.Interaction], message, reason):
    embed = discord.Embed(title="New report", colour=discord.Color.red(), url=message.jump_url,
                          description=f"Reason: {reason}" if reason else "")
    embed.add_field(name="Message Content",
                    value=f"{message.content[:1900]}{'...' if message.content[:1900] != message.content else ''}",
                    inline=False)
    if isinstance(ctx, commands.Context):
        embed.add_field(name="Reported By", value=f"{ctx.author.mention} ({ctx.author})", inline=False)
    else:
        embed.add_field(name="Reported By", value=f"{ctx.user.mention} ({ctx.user})", inline=False)
    embed.set_author(name=message.author, icon_url=message.author.avatar)
    if message.attachments:
        embed.set_image(url=message.attachments[0].url)
    await ctx.guild.get_channel(Channel.REPORTS_APPEALS).send(embed=embed)


async def warn_punishments(ctx, user):
    warns = [z async for z in ctx.bot.moderation_coll.find({"offender_id": user.id, "expired": False})]
    config = await get_config(ctx.bot)
    score = sum([SEVERITY[z["type"]] for z in warns if z["type"] == "warn" or z["mod_id"] != ctx.bot.user.id])
    punishment = config["punishForWarns"][str(score)] if str(score) in config["punishForWarns"] else None
    if not punishment:
        if int(list(config["punishForWarns"].keys())[-1]) < score:
            await ctx.invoke(ctx.bot.get_command("ban"), user, 31536000, reason="maximum warning limit exceeded")
        return
    ctx.author = ctx.guild.me
    cmd = ctx.bot.get_command(punishment["type"].lower())
    if not cmd:
        return
    if cmd.name == "kick":
        return await ctx.invoke(cmd, user, reason=f"{score} warnings")
    await ctx.invoke(cmd, user, punishment["duration"], reason=f"{score} warnings")


async def end_punishment(bot, payload, moderator, reason):
    try:
        guild = bot.get_guild(Misc.GUILD)
        if payload["type"] == "mute":
            member = guild.get_member(payload["offender_id"])
            await member.remove_roles(guild.get_role((await get_config(bot))["mutedRole"]))
        elif payload["type"] == "ban":
            await guild.unban(BannedUser(payload["offender_id"]), reason="punishment ended")
        await end_log(bot, payload, moderator=moderator, reason=reason)
    except:
        return


def chat_embed(ctx, payload):
    offender = ctx.bot.get_user(payload["offender_id"])
    embed = discord.Embed(title=f"**{PAST_PARTICIPLES[payload['type']]}**", colour=COLOURS[payload["type"]],
                          description=payload["reason"] if payload["reason"] else "")\
        .set_author(name=offender, icon_url=offender.avatar)
    return embed


def mass_ban_chat_embed(ctx, payload):
    mod = ctx.guild.get_member(payload["mod_id"])
    embed = discord.Embed(title="Mass Ban", colour=COLOURS["ban"],
                          description=payload["offenders_string"][:1900] + ("\n..." if len(payload["offenders_string"]) > 400 else ""))\
        .set_author(name=mod, icon_url=mod.avatar)
    return embed


async def end_log(bot, payload, *, moderator, reason):
    user = bot.get_user(payload["offender_id"])
    embed = discord.Embed(title=f"Un{payload['type']}", colour=discord.Colour.green())\
        .set_author(name=(user or "not found"), icon_url=(user.avatar if hasattr(user, "avatar") else ""))\
        .set_footer(text=f"Offender ID: {payload['offender_id']}")
    embed.add_field(name="Reason", value=reason, inline=False)
    embed.add_field(name="Moderator", value=moderator if moderator == "Automod" else moderator.mention, inline=False)
    # TODO: make a inverse of stringToSeconds() to format an integer value of seconds
    # if "duration" in payload:
    #     embed.add_field(name="Duration", value=payload["duration"], inline=False)
    await bot.get_guild(Misc.GUILD).get_channel(Channel.MOD_LOGS).send(embed=embed)


async def log(bot, payload):
    log_lockdown(bot, payload)
    offender = bot.get_user(payload["offender_id"])
    embed = discord.Embed(title=payload["type"].capitalize(), colour=COLOURS[payload["type"]])\
        .set_author(name=offender, icon_url=offender.avatar)
    embed.add_field(name="Reason", value=payload["reason"], inline=False)
    embed.add_field(name="Moderator", value=f"<@{payload['mod_id']}>", inline=False)
    if "duration" in payload and payload["duration"]:
        embed.add_field(name="Duration", value=payload["duration_string"])
    embed.set_footer(text=f"Case ID: {payload['id']}")
    embed.timestamp = datetime.datetime.now()
    await bot.get_guild(Misc.GUILD).get_channel(Channel.MOD_LOGS).send(embed=embed)


async def log_mass(bot, payload):
    log_lockdown(bot, payload)
    dt = datetime.datetime.now()
    with open(f"mass_bans/{dt.strftime('%M-%S--%d%m%y')}.txt", "w") as f:
        f.write(f"Mass Ban\n{dt.strftime('%M:%S %d/%m/%Y')}\n\n" + "\n".join(
                [f"{z} - {z.id}" for z in payload["offenders"]]))
    mod = bot.get_user(payload["mod_id"])
    embed = discord.Embed(title=f"Mass {payload['type']}", colour=COLOURS[payload["type"]])
    embed.add_field(name="Reason", value=f"Mass {payload['type']}", inline=False)
    embed.add_field(name="Moderator", value=mod.mention, inline=False)
    if "duration" in payload and payload["duration"]:
        embed.add_field(name="Duration", value=payload["duration_string"], inline=False)
    embed.add_field(name="Offenders", value=payload["offenders_string"][:1900], inline=False)
    embed.set_footer(text=f"Case ID: {payload['id']}")
    embed.timestamp = dt
    await bot.get_guild(Misc.GUILD).get_channel(Channel.MOD_LOGS).send(embed=embed)


async def log_channel_lock(ctx, channel, _type):
    embed = Embed(ctx.author, description=f"{channel.mention} was {_type}ed by {ctx.author.mention}",
                  colour=0xFF0000 if _type == "lock" else discord.Colour.green())
    embed.auto_author().timestamp_now()
    await ctx.guild.get_channel(Channel.MOD_LOGS).send(embed=embed)


def log_lockdown(bot, payload):
    bot_config = get_file_json("config")
    if not bot_config["lockdown"]:
        return
    if payload["type"].upper() not in ["BAN", "KICK"]:
        return
    if "offenders" in payload:
        for offender in payload["offenders"]:
            lockdown_data[offender.id] = {
                "name": str(offender),
                "type": payload["type"],
                "reason": payload["reason"]
            }
    else:
        lockdown_data[payload["offender_id"]] = {
            "name": str(bot.get_user(payload["offender_id"])),
            "type": payload["type"],
            "reason": payload["reason"]
        }


def get_lockdown_log():
    return lockdown_data


def reset_lockdown_log():
    lockdown_data.clear()
