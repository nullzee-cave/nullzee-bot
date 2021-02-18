import discord
from discord.ext import commands, tasks
from api_key import moderationColl
import time
from helpers import moderationUtils
import re 

INVITE_REGEX = "discord.gg\/(\w{6})"

class Automod(commands.Cog): # this is for timed punishments, removing warns etc.

    def __init__(self, bot, hidden):
        self.hidden = hidden
        self.bot: commands.Bot = bot
        self.delete_warns.start()
        self.timed_punishments.start()

    @commands.Cog.listener()
    async def on_ready(self):
        await moderationUtils.update_config()

    @commands.Cog.listener()
    async def on_message(self, message):
        if not message.guild:
            return
        if message.author.guild_permissions.manage_messages:
            return
        ctx = await self.bot.get_context(message)
        ctx.author = message.guild.me
        config = await moderationUtils.get_config()
        if config["mentions"]["val"] <= len(message.mentions) and message.channel.id not in config["mentions"]["allowed_channels"]:
            await ctx.invoke(self.bot.get_command('warn'), message.author, reason="Mass mention")
        if config["invites"]["action"] == "warn" and message.channel.id not in config["invites"]["allowed_channels"] and re.match(INVITE_REGEX, message.content, re.IGNORECASE):
            await ctx.invoke(self.bot.get_command('warn'), message.author, reason="Invite link")
        if config["invites"]["action"] == "delete" and message.channel.id not in config["invites"]["allowed_channels"] and re.match(INVITE_REGEX, message.content, re.IGNORECASE):
            await message.delete()
        for word in config["badWords"]:
            if re.findall(word, message.content, flags=re.IGNORECASE):
                if config["badWords"][word] == "delete":
                    await message.delete()
                elif config["badWords"][word] == "warn":
                    await ctx.invoke(self.bot.get_command('warn'), message.author, reason="Disallowed word/phrase")
                elif config["badWords"][word] == "kick":
                    await ctx.invoke(self.bot.get_command("kick"), message.author, reason="Disallowed word/phrase")
                elif config["badWords"][word] == "ban":
                    await ctx.invoke(self.bot.get_command("ban"), message.author, reason="Disallowed word/phrase")
                elif config["badWords"][word] == "report":
                    await ctx.invoke(self.bot.get_command("report"), message, reason="Disallowed word/phrase")
                    continue
                else:
                    continue
                await ctx.invoke(self.bot.get_command("report"), message,
                                 reason=f"{moderationUtils.PAST_PARTICIPLES[config['badWords'][word]]} by automod for this message")


    @tasks.loop(minutes=1)
    async def delete_warns(self):
        async for warn in moderationColl.find({"expired": False}):
            if warn["timestamp"] + (await moderationUtils.get_config())["deleteWarnsAfter"] < time.time():
                await moderationColl.update_one(warn, {"$set": {"expired": True}})

    @tasks.loop(minutes=1)
    async def timed_punishments(self):
        async for punishment in moderationColl.find({"active": True, "permanent": False}):
            if punishment["ends"] < time.time():
                await moderationUtils.end_punishment(self.bot, punishment, moderator="automod", reason="punishment served")
                await moderationColl.update_one(punishment, {"$set": {"active": False}})

    @commands.Cog.listener()
    async def on_member_join(self, member):
        if await moderationColl.find_one({"offender_id": member.id, "active": True, "type": "mute"}):
            await member.add_roles(member.guild.get_role((await moderationUtils.get_config())["muteRole"]))

def setup(bot):
    bot.add_cog(Automod(bot, True))
