from discord.ext import commands
import discord
from perks import achievements
from helpers.events import Emitter


class ShallowContext:
    def __init__(self):
        self.channel = None
        self.author = None
        self.guild = None

    @classmethod
    async def create(cls, member: discord.Member):
        self = cls()
        self.channel = (member.dm_channel or await member.create_dm())
        self.author = member
        self.guild = member.guild
        return self

    async def send(self, *args, **kwargs):
        return await self.channel.send(*args, **kwargs)

class Achivements(commands.Cog):

    def __init__(self, bot):
        self.hidden = True
        self.bot: commands.Bot = bot
        self.emitter = Emitter()

    @commands.Cog.listener()
    async def on_message(self, message):
        await self.emitter.emit("message", await self.bot.get_context(message))

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        if before.roles != after.roles:
            await self.emitter.emit("update_roles", await ShallowContext.create(after), after.roles)

    @commands.Cog.listener()
    async def on_command(self, ctx):
        await self.emitter.emit("command", ctx, ctx.command.name)


def setup(bot):
    bot.add_cog(Achivements(bot))
