import discord
from discord.ext import commands, tasks
from api_key import moderationColl
import time
from helpers import moderationUtils

class Automod(commands.Cog): # this is for timed punishments, removing warns etc.

    def __init__(self, bot, hidden):
        self.hidden = hidden
        self.bot: commands.Bot = bot
        self.delete_warns.start()
        self.timed_punishments.start()

    @tasks.loop(minutes=1)
    async def delete_warns(self):
        async for warn in moderationColl.find({"type": "warn"}):
            if warn["timestamp"] + moderationUtils.DELETE_WARNS_AFTER:
                await moderationColl.delete_one(warn)

    @tasks.loop(minutes=1)
    async def timed_punishments(self):
        async for punishment in moderationColl.find({"active": True, "permanent": False}):
            if punishment["ends"] < time.time():
                await moderationUtils.end_punishment(self.bot, punishment, moderator="automod", reason="punishment served")
                await moderationColl.update_one(punishment, {"$set": {"active": False}})

def setup(bot):
    bot.add_cog(Automod(bot, True))