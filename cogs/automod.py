import discord
from discord.ext import commands, tasks
from api_key import moderation_coll
import time
from helpers import moderation_utils, utils
import re

INVITE_REGEX = "discord.gg\/(\w{6})"


class Automod(commands.Cog, name="Automod"):
    """Automod, for automatic punishments, timed punishments, removing warns, etc"""

    def __init__(self, bot, hidden):
        self.hidden = hidden
        self.bot: commands.Bot = bot
        self.delete_warns.start()
        self.timed_punishments.start()

    @commands.Cog.listener()
    async def on_ready(self):
        await moderation_utils.update_config()

    @commands.Cog.listener()
    async def on_message(self, message):
        if not (message.guild or isinstance(message.author, discord.Member)) or type(message.author) == discord.User:
            return
        if message.author.guild_permissions.manage_messages:
            return
        ctx = await self.bot.get_context(message)
        ctx.author = message.guild.me
        config = await moderation_utils.get_config()
        if config["mentions"]["val"] <= len(message.mentions) and \
           message.channel.id not in config["mentions"]["allowed_channels"]:
            if config["mentions"]["action"] == "warn":
                await ctx.invoke(self.bot.get_command("warn"), message.author, reason="Mass mention")
            elif config["mentions"]["action"] == "mute":
                await ctx.invoke(self.bot.get_command("mute"), message.author, 86400, reason="Mass mention")
        if config["invites"]["action"] == "warn" and \
           message.channel.id not in config["invites"]["allowed_channels"] and \
           re.match(INVITE_REGEX, message.content, re.IGNORECASE):
            await ctx.invoke(self.bot.get_command("warn"), message.author, reason="Invite link")
        if config["invites"]["action"] == "delete" and \
           message.channel.id not in config["invites"]["allowed_channels"] and \
           re.match(INVITE_REGEX, message.content, re.IGNORECASE):
            await message.delete()
        clean_content = utils.clean_message_content(message.content)
        for word in config["badWords"]:
            if re.findall(word, clean_content, flags=re.IGNORECASE):
                if config["badWords"][word] == "delete":
                    await message.delete()
                elif config["badWords"][word] == "warn":
                    await ctx.invoke(self.bot.get_command("warn"), message.author, reason="Disallowed word/phrase")
                elif config["badWords"][word] == "kick":
                    await ctx.invoke(self.bot.get_command("kick"), message.author, reason="Disallowed word/phrase")
                elif config["badWords"][word] == "ban":
                    # If the author is going to be banned, report first then continue to avoid double reporting
                    await ctx.invoke(self.bot.get_command("report"), message,
                                     reason=f"{moderation_utils.PAST_PARTICIPLES[config['badWords'][word]]} "
                                            f"by automod for this message in {ctx.channel.mention}")
                    await ctx.invoke(self.bot.get_command("ban"), message.author, reason="Disallowed word/phrase")
                    continue
                elif config["badWords"][word] == "report":
                    await moderation_utils.send_report(ctx, message, "Disallowed word/phrase")
                    continue
                else:
                    continue

                await ctx.invoke(self.bot.get_command("report"), message,
                                 reason=f"{moderation_utils.PAST_PARTICIPLES[config['badWords'][word]]} "
                                        f"by automod for this message in {ctx.channel.mention}")

        for link in config["scamLinks"]:
            formatted_link = link.replace(";", ":").replace(",", ".")
            if re.findall(formatted_link, clean_content, flags=re.IGNORECASE):
                if config["scamLinks"][link] == "ban":
                    await ctx.invoke(self.bot.get_command("ban"), message.author,
                                     reason="Scam Links. When you regain access to your account, please DM a staff "
                                            "member or rejoin and open a ticket on another account to be unbanned.")
                elif config["scamLinks"][link] == "delete":
                    await ctx.message.delete()

    @tasks.loop(minutes=1)
    async def delete_warns(self):
        async for warn in moderation_coll.find({"expired": False}):
            if warn["timestamp"] + (await moderation_utils.get_config())["deleteWarnsAfter"] < time.time():
                await moderation_coll.update_one(warn, {"$set": {"expired": True}})

    @delete_warns.before_loop
    async def before_delete_warns(self):
        await self.bot.wait_until_ready()

    @tasks.loop(minutes=1)
    async def timed_punishments(self):
        async for punishment in moderation_coll.find({"active": True, "permanent": False}):
            if punishment["ends"] < time.time():
                await moderation_utils.end_punishment(self.bot, punishment, moderator="automod",
                                                      reason="Punishment served")
                await moderation_coll.update_one(punishment, {"$set": {"active": False}})

    @timed_punishments.before_loop
    async def before_timed_punishments(self):
        await self.bot.wait_until_ready()

    @commands.Cog.listener()
    async def on_member_join(self, member):
        await moderation_utils.automod_name(member)
        if await moderation_coll.find_one({"offender_id": member.id, "active": True, "type": "mute"}):
            await member.add_roles(member.guild.get_role((await moderation_utils.get_config())["mutedRole"]))

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        await moderation_utils.automod_name(after)


async def setup(bot):
    await bot.add_cog(Automod(bot, True))
