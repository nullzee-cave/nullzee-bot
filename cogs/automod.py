import discord
from discord.ext import commands, tasks
from api_key import moderationColl


class Automod(commands.Cog): # this is for timed punishments, removing warns etc.

    def __init__(self, bot, hidden):
        self.hidden = hidden
        self.bot: commands.Bot = bot


def setup(bot):
    bot.add_cog(Automod(bot, True))